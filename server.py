#!/usr/bin/env python3
import os, html, tarfile, argparse, json, datetime, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, quote, urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class FileServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/"))
        fs = os.path.join(self.server.serve_root, rel)
        qs = parse_qs(parsed.query)

        # Serve frontend static files
        if rel in ("index.html", "styles.css", "script.js"):
            return self.serve_static(os.path.join(BASE_DIR, rel))

        # JSON directory listing
        if qs.get("json") == ["1"] and os.path.isdir(fs):
            return self.serve_json_dir(fs, parsed.path)

        # Folder download as .tar.gz
        if qs.get("download") == ["zip"] and os.path.isdir(fs):
            return self.serve_archive(fs)

        # Serve raw file
        if os.path.isfile(fs):
            return self.serve_file(fs)

        # Serve main index.html (UI)
        if os.path.isdir(fs):
            return self.serve_dir(parsed.path)

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        rel = unquote(parsed.path.lstrip("/"))
        target = os.path.join(self.server.serve_root, rel)
        
        if not os.path.isdir(target):
            return self.send_error(400, "Upload target is not a directory")

        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            return self.send_error(400, "Expected multipart/form-data")

        boundary = ctype.split("boundary=", 1)[1].encode()
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        parts = data.split(b"--" + boundary)
        uploaded_files = []
        
        for part in parts:
            if b'Content-Disposition' not in part:
                continue
            try:
                header, body = part.split(b"\r\n\r\n", 1)
                header = header.decode(errors="ignore")
                if 'filename="' not in header:
                    continue
                fname = header.split('filename="', 1)[1].split('"', 1)[0]
                if not fname:  # Skip empty filenames
                    continue
                safe = os.path.basename(fname)
                body = body.rsplit(b"\r\n", 1)[0]
                
                file_path = os.path.join(target, safe)
                with open(file_path, "wb") as f:
                    f.write(body)
                uploaded_files.append(safe)
            except Exception as e:
                print(f"Upload error: {e}")
                continue

        # Return JSON response with upload status
        response_data = {
            "status": "success",
            "uploaded_files": uploaded_files,
            "count": len(uploaded_files)
        }
        
        response_json = json.dumps(response_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json)

    def serve_static(self, path):
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
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error serving static file: {str(e)}")

    def serve_file(self, path):
        try:
            # Check if file exists and is readable
            if not os.path.exists(path):
                return self.send_error(404, "File not found")
            
            if not os.access(path, os.R_OK):
                return self.send_error(403, "Permission denied")
            
            # Get file size
            file_size = os.path.getsize(path)
            
            # Determine content type using mimetypes module
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type is None:
                mime_type = "application/octet-stream"
            
            # Get filename for Content-Disposition
            filename = os.path.basename(path)
            
            # Handle range requests for large files
            range_header = self.headers.get('Range')
            if range_header:
                return self.serve_file_range(path, range_header, file_size, mime_type, filename)
            
            # Serve entire file
            with open(path, "rb") as f:
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                
                # For downloads, use attachment; for viewable files, use inline
                if self.should_download(mime_type):
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                else:
                    self.send_header("Content-Disposition", f'inline; filename="{filename}"')
                
                self.end_headers()
                
                # Stream the file in chunks to handle large files
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except Exception as e:
            print(f"Error serving file {path}: {e}")
            self.send_error(500, f"Error serving file: {str(e)}")

    def serve_file_range(self, path, range_header, file_size, mime_type, filename):
        """Handle HTTP range requests for partial content"""
        try:
            # Parse range header (e.g., "bytes=0-1023")
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
            
            # Validate range
            if start >= file_size or end >= file_size or start > end:
                self.send_error(416, "Requested Range Not Satisfiable")
                return
            
            content_length = end - start + 1
            
            with open(path, "rb") as f:
                f.seek(start)
                
                self.send_response(206)  # Partial Content
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(content_length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                
                if self.should_download(mime_type):
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                else:
                    self.send_header("Content-Disposition", f'inline; filename="{filename}"')
                
                self.end_headers()
                
                # Stream the requested range
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
        """Determine if file should be downloaded or viewed inline"""
        viewable_types = [
            'text/', 'image/', 'audio/', 'video/',
            'application/pdf', 'application/json',
            'application/javascript'
        ]
        return not any(mime_type.startswith(vt) for vt in viewable_types)

    def serve_archive(self, folder_path):
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
        try:
            index_path = os.path.join(BASE_DIR, "index.html")
            if not os.path.exists(index_path):
                return self.send_error(500, "Missing index.html")
            
            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Replace template variables
            html_content = html_content.replace("{{PATH}}", html.escape(url_path))
            html_data = html_content.encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html_data)
        except Exception as e:
            print(f"Error serving directory {url_path}: {e}")
            self.send_error(500, f"Error serving directory: {str(e)}")

    def serve_json_dir(self, path, url_path):
        try:
            files = []
            
            # Add parent directory link if not at root
            if url_path != "/":
                parent_path = "/".join(url_path.rstrip("/").split("/")[:-1]) or "/"
                files.append({
                    "name": "..",
                    "is_dir": True,
                    "size": 0,
                    "modified": "",
                    "path": parent_path
                })
            
            # List directory contents
            for name in sorted(os.listdir(path), key=str.lower):
                if name.startswith('.'):  # Skip hidden files
                    continue
                    
                full = os.path.join(path, name)
                try:
                    stat = os.stat(full)
                    files.append({
                        "name": name,
                        "is_dir": os.path.isdir(full),
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                except OSError:
                    # Skip files that can't be accessed
                    continue
            
            result = {
                "path": url_path,
                "entries": files
            }
            
            data = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            self.send_error(500, f"Error listing directory: {str(e)}")

    def log_message(self, format, *args):
        """Custom log message to make it more readable"""
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeoShare - Modern File Server")
    parser.add_argument("-r", "--root", default=os.getcwd(), help="Directory to serve (default: current directory)")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f"Error: Directory '{args.root}' does not exist")
        exit(1)

    httpd = HTTPServer((args.host, args.port), FileServer)
    httpd.serve_root = os.path.abspath(args.root)
    
    print("=" * 50)
    print("🚀 NeoShare File Server")
    print("=" * 50)
    print(f"📡 Server running at http://{args.host}:{args.port}/")
    print(f"📁 Serving files from: {httpd.serve_root}")
    print(f"🔧 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.shutdown()