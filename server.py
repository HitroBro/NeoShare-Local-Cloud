#!/usr/bin/env python3
import os
import html
import tarfile
import argparse
import json
import datetime
import mimetypes
import time
import hashlib
import secrets
import base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse, parse_qs
from collections import defaultdict

# Directory containing UI assets (index.html, styles.css, script.js)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Hard cap for uploads to reduce memory/DoS risk
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
STREAM_CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer

# Rate limiting: per-IP upload tracking
UPLOAD_RATE_LIMIT = defaultdict(list)  # IP -> list of timestamps
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # max uploads per minute per IP

# Optional basic auth (set via environment variables)
AUTH_USER = os.environ.get("NEOSHARE_USER")
AUTH_PASS = os.environ.get("NEOSHARE_PASS")


class FileServer(BaseHTTPRequestHandler):
    def check_auth(self):
        """Verify HTTP Basic Auth credentials if configured."""
        if not (AUTH_USER and AUTH_PASS):
            return True
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            self.send_unauthorized()
            return False
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            if ":" not in decoded:
                self.send_unauthorized()
                return False
            user, pwd = decoded.split(":", 1)
            # Use constant-time comparison to mitigate timing attacks
            user_valid = secrets.compare_digest(user, AUTH_USER)
            pwd_valid = secrets.compare_digest(pwd, AUTH_PASS)
            if not (user_valid and pwd_valid):
                self.send_unauthorized()
                return False
            return True
        except Exception:
            self.send_unauthorized()
            return False

    def send_unauthorized(self):
        """Send 401 Unauthorized response with WWW-Authenticate header."""
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="NeoShare", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "12")
        self.end_headers()
        self.wfile.write(b"Unauthorized")

    def do_GET(self):
        # Enforce authentication on all GET requests
        if not self.check_auth():
            return

        # Parse URL path and query parameters
        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/"))
        qs = parse_qs(parsed.query)

        # Resolve requested path and block directory traversal attempts
        serve_root = os.path.abspath(self.server.serve_root)
        target_path = os.path.realpath(os.path.join(serve_root, rel))
        try:
            common = os.path.commonpath([serve_root, target_path])
        except ValueError:
            common = ''
        if common != serve_root:
            self.log_message("SECURITY ALERT: Path traversal attempt blocked: %s", rel)
            return self.send_error(403, "Forbidden: Access Denied")

        fs = target_path

        # Serve UI assets from the script directory
        if rel in ("index.html", "styles.css", "script.js"):
            return self.serve_static(os.path.join(BASE_DIR, rel))

        # Return directory listing as JSON (used by frontend)
        if qs.get("json") == ["1"] and os.path.isdir(fs):
            return self.serve_json_dir(fs, parsed.path)

        # Download a folder as a streamed .tar.gz archive
        if qs.get("download") == ["zip"] and os.path.isdir(fs):
            return self.serve_archive(fs)

        # Serve a file (supports Range requests for resumable downloads/streaming)
        if os.path.isfile(fs):
            return self.serve_file(fs)

        # Serve the main UI for directory browsing
        if os.path.isdir(fs):
            return self.serve_dir(parsed.path)

        self.send_error(404, "Not Found")

    def parse_streaming_multipart(self, length, boundary, target_dir):
        """Stream multipart form data directly to disk without buffering in RAM."""
        dash_boundary = b"--" + boundary
        uploaded_files = []
        bytes_left = length

        def read_bytes(n):
            nonlocal bytes_left
            to_read = min(n, bytes_left)
            if to_read <= 0:
                return b""
            chunk = self.rfile.read(to_read)
            bytes_left -= len(chunk)
            return chunk

        buffer = b""
        def read_line():
            nonlocal buffer
            while b"\r\n" not in buffer and bytes_left > 0:
                chunk = read_bytes(STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                buffer += chunk
            if b"\r\n" in buffer:
                line, buffer = buffer.split(b"\r\n", 1)
                return line
            line, buffer = buffer, b""
            return line

        # 1. Skip to initial boundary delimiter
        first_line = read_line()
        while first_line and dash_boundary not in first_line:
            first_line = read_line()

        if not first_line or first_line.endswith(b"--"):
            return uploaded_files

        # 2. Process sequential multipart sections
        while True:
            headers = {}
            while True:
                hline = read_line()
                if not hline:
                    break
                try:
                    htext = hline.decode("utf-8", errors="ignore")
                    if ":" in htext:
                        k, v = htext.split(":", 1)
                        headers[k.strip().lower()] = v.strip()
                except Exception:
                    pass

            disp = headers.get("content-disposition", "")
            filename = None
            if 'filename="' in disp:
                filename = disp.split('filename="', 1)[1].split('"', 1)[0]
            elif "filename='" in disp:
                filename = disp.split("filename='", 1)[1].split("'", 1)[0]

            current_file = None
            current_path = None
            if filename:
                safe = os.path.basename(filename).strip()
                if safe:
                    current_path = os.path.join(target_dir, safe) # path sanitization
                    current_file = open(current_path, "wb", buffering=64*1024)
                    uploaded_files.append(safe)

            marker = b"\r\n" + dash_boundary
            marker_len = len(marker)

            while True:
                while len(buffer) < marker_len + 4 and bytes_left > 0:
                    chunk = read_bytes(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    buffer += chunk

                idx = buffer.find(marker)
                if idx != -1:
                    body_chunk = buffer[:idx]
                    if current_file:
                        current_file.write(body_chunk)
                        current_file.close()
                        current_file = None

                    buffer = buffer[idx + marker_len:]
                    if buffer.startswith(b"--"):
                        read_bytes(bytes_left)
                        return uploaded_files
                    if buffer.startswith(b"\r\n"):
                        buffer = buffer[2:]
                    break
                else:
                    if bytes_left == 0:
                        if current_file:
                            current_file.write(buffer)
                            current_file.close()
                            current_file = None
                        return uploaded_files

                    safe_len = len(buffer) - marker_len
                    if safe_len > 0:
                        if current_file:
                            current_file.write(buffer[:safe_len])
                        buffer = buffer[safe_len:]

        return uploaded_files

    def send_security_headers(self):
        """Send baseline OWASP security headers on all responses."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def do_HEAD(self):
        """Handle HEAD requests by sending identical headers as GET without body."""
        if not self.check_auth():
            return
        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/"))
        serve_root = os.path.realpath(self.server.serve_root)
        target_path = os.path.realpath(os.path.join(serve_root, rel))

        try:
            common = os.path.commonpath([serve_root, target_path])
        except ValueError:
            common = ''
        if common != serve_root:
            return self.send_error(403, "Forbidden: Access Denied")

        fs = target_path
        if rel in ("index.html", "styles.css", "script.js"):
            path = os.path.join(BASE_DIR, rel)
            mime = "text/plain"
            if path.endswith(".css"): mime = "text/css"
            elif path.endswith(".js"): mime = "application/javascript"
            elif path.endswith(".html"): mime = "text/html"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(os.path.getsize(path)))
            self.send_security_headers()
            self.end_headers()
            return

        if os.path.isfile(fs):
            mime_type, _ = mimetypes.guess_type(fs)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.send_header("Content-Length", str(os.path.getsize(fs)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_security_headers()
            self.end_headers()
            return

        if os.path.isdir(fs):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_security_headers()
            self.end_headers()
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        # Enforce authentication on POST requests
        if not self.check_auth():
            return

        # Rate limiting check
        client_ip = self.client_address[0]
        now = time.time()
        # Clean old timestamps and remove inactive IPs
        active_ips = [ip for ip in list(UPLOAD_RATE_LIMIT.keys())]
        for ip in active_ips:
            UPLOAD_RATE_LIMIT[ip] = [ts for ts in UPLOAD_RATE_LIMIT[ip] if now - ts < RATE_LIMIT_WINDOW]
            if not UPLOAD_RATE_LIMIT[ip]:
                del UPLOAD_RATE_LIMIT[ip]
        if len(UPLOAD_RATE_LIMIT[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            self.log_message("RATE LIMIT: Upload rejected for %s (too many requests)", client_ip)
            self.send_response(429)
            self.send_header("Retry-After", str(RATE_LIMIT_WINDOW))
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Too Many Requests - Upload rate limit exceeded")
            return
        UPLOAD_RATE_LIMIT[client_ip].append(now)

        # Validate Content-Length (required for safe read sizing)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self.send_error(400, "Invalid Content-Length")

        # Enforce upload size limit before reading request body
        if length > MAX_UPLOAD_SIZE:
            self.log_message("SECURITY ALERT: Upload exceeded limit (%d bytes)", length)
            return self.send_error(413, f"Payload Too Large (Max {MAX_UPLOAD_SIZE/1024/1024/1024}GB)")

        # Resolve upload destination and block traversal
        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/"))
        serve_root = os.path.abspath(self.server.serve_root)
        target = os.path.realpath(os.path.join(serve_root, rel))
        try:
            common = os.path.commonpath([serve_root, target])
        except ValueError:
            common = ''
        if common != serve_root:
            return self.send_error(403, "Forbidden")

        # Uploads are only allowed into existing directories
        if not os.path.isdir(target):
            return self.send_error(400, "Upload target is not a directory")

        # Accept multipart/form-data uploads (simple parser)
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            return self.send_error(400, "Expected multipart/form-data")

        try:
            boundary = ctype.split("boundary=", 1)[1].strip().strip('"').encode()
        except Exception:
            return self.send_error(400, "Malformed boundary in Content-Type")

        try:
            uploaded_files = self.parse_streaming_multipart(length, boundary, target)
        except Exception as e:
            self.log_message("Upload streaming exception: %s", str(e))
            return self.send_error(500, f"Upload processing error: {str(e)}")

        # Return upload result as JSON for frontend consumption
        response_data = {
            "status": "success",
            "uploaded_files": uploaded_files,
            "count": len(uploaded_files),
        }
        response_json = json.dumps(response_data).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json)

    def serve_static(self, path):
        # Serve bundled frontend files with correct MIME types
        if not os.path.isfile(path):
            return self.send_error(404, "Static file not found")

        mime = "text/plain"
        if path.endswith(".css"):
            mime = "text/css"
        elif path.endswith(".js"):
            mime = "application/javascript"
        elif path.endswith(".html"):
            mime = "text/html"

        try:
            with open(path, "rb") as f:
                data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_security_headers()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error serving static file: {str(e)}")

    def serve_file(self, path):
        # Serve a single file; supports byte ranges for streaming/resume
        try:
            if not os.path.exists(path):
                return self.send_error(404, "File not found")

            if not os.access(path, os.R_OK):
                return self.send_error(403, "Permission denied")

            file_size = os.path.getsize(path)

            mime_type, _ = mimetypes.guess_type(path)
            if mime_type is None:
                mime_type = "application/octet-stream"

            filename = os.path.basename(path)

            range_header = self.headers.get("Range")
            if range_header:
                return self.serve_file_range(path, range_header, file_size, mime_type, filename)

            with open(path, "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")

                disp = "attachment" if self.should_download(mime_type) else "inline"
                self.send_header("Content-Disposition", f'{disp}; filename="{filename}"')
                self.send_security_headers()
                self.end_headers()

                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except Exception as e:
            print(f"Error serving file {path}: {e}")
            self.send_error(500, f"Error serving file: {str(e)}")

    def serve_file_range(self, path, range_header, file_size, mime_type, filename):
        # Respond to "Range: bytes=start-end" requests
        try:
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1

            if start >= file_size or end >= file_size or start > end:
                self.send_error(416, "Requested Range Not Satisfiable")
                return

            content_length = end - start + 1

            with open(path, "rb") as f:
                f.seek(start)

                self.send_response(206)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(content_length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")

                disp = "attachment" if self.should_download(mime_type) else "inline"
                self.send_header("Content-Disposition", f'{disp}; filename="{filename}"')

                self.end_headers()

                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        except Exception as e:
            print(f"Error serving file range {path}: {e}")
            self.send_error(500, f"Error serving file range: {str(e)}")

    def should_download(self, mime_type):
        # Decide whether to render inline or force download based on MIME type
        viewable_types = [
            "text/",
            "image/",
            "audio/",
            "video/",
            "application/pdf",
            "application/json",
            "application/javascript",
        ]
        return not any(mime_type.startswith(vt) for vt in viewable_types)

    def serve_archive(self, folder_path):
        # Stream a tar.gz archive directly to the client (no temp file)
        try:
            folder_name = os.path.basename(folder_path.rstrip(os.sep)) or "download"

            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Disposition", f'attachment; filename="{folder_name}.tar.gz"')
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            with tarfile.open(fileobj=self.wfile, mode="w|gz") as tar:
                tar.add(folder_path, arcname=folder_name)

        except Exception as e:
            print(f"Error creating archive for {folder_path}: {e}")
            self.send_error(500, f"Error creating archive: {str(e)}")

    def serve_dir(self, url_path):
        # Serve the main HTML UI and inject the current path placeholder
        try:
            index_path = os.path.join(BASE_DIR, "index.html")
            if not os.path.exists(index_path):
                return self.send_error(500, "Missing index.html")

            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            html_content = html_content.replace("{{PATH}}", html.escape(url_path))
            html_data = html_content.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_security_headers()
            self.end_headers()
            self.wfile.write(html_data)
        except Exception as e:
            print(f"Error serving directory {url_path}: {e}")
            self.send_error(500, f"Error serving directory: {str(e)}")

    def serve_json_dir(self, path, url_path):
        # Produce a JSON listing of a directory for frontend rendering
        try:
            files = []

            # Add a virtual parent entry for navigation
            if url_path != "/":
                parent_path = "/".join(url_path.rstrip("/").split("/")[:-1]) or "/"
                files.append(
                    {
                        "name": "..",
                        "is_dir": True,
                        "size": 0,
                        "modified": "",
                        "path": parent_path,
                    }
                )

            # List files (skip dotfiles)
            for name in sorted(os.listdir(path), key=str.lower):
                if name.startswith("."):
                    continue
                full = os.path.join(path, name)
                try:
                    stat = os.stat(full)
                    files.append(
                        {
                            "name": name,
                            "is_dir": os.path.isdir(full),
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )
                except OSError:
                    continue

            result = {"path": url_path, "entries": files}
            data = json.dumps(result, indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_security_headers()
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            self.send_error(500, f"Error listing directory: {str(e)}")

    def log_message(self, format, *args):
        # Timestamped server logs (matches BaseHTTPRequestHandler style)
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")


if __name__ == "__main__":
    # CLI arguments: root directory, host binding, port
    parser = argparse.ArgumentParser(description="NeoShare - Modern File Server")
    parser.add_argument("-r", "--root", default=os.getcwd(), help="Directory to serve (default: current directory)")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    # Ensure the serving root exists
    if not os.path.isdir(args.root):
        print(f"Error: Directory '{args.root}' does not exist")
        raise SystemExit(1)

    # ThreadingHTTPServer allows concurrent clients
    httpd = ThreadingHTTPServer((args.host, args.port), FileServer)
    httpd.serve_root = os.path.abspath(args.root)

    print("=" * 50)
    print("🚀 NeoShare File Server (Threaded + Hardened)")
    print("=" * 50)
    display_host = "localhost" if args.host == "0.0.0.0" else args.host
    print(f"📡 Server running at http://{display_host}:{args.port}/")
    print(f"📁 Serving files from: {httpd.serve_root}")
    print("🔧 Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.shutdown()

# Verified streaming upload engine v1.2.0