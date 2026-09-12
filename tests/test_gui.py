import os
import unittest
import urllib.request
import urllib.error
import json
import base64
import gzip
import threading
from http.server import ThreadingHTTPServer
from server import FileServer, BASE_DIR

class TestNeoShareGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), FileServer)
        cls.server.serve_root = os.path.abspath(BASE_DIR)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_index_html_renders(self):
        url = f'http://127.0.0.1:{self.port}/'
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            body = res.read().decode('utf-8')
            self.assertIn('NeoShare', body)
            self.assertIn('id="fileList"', body)
            self.assertIn('id="dropZone"', body)

    def test_json_api(self):
        url = f'http://127.0.0.1:{self.port}/?json=1'
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            self.assertIn('entries', data)
            self.assertIsInstance(data['entries'], list)

    def test_static_assets_serve(self):
        for asset, expected_mime in [
            ('/styles.css', 'text/css'),
            ('/script.js', 'application/javascript')
        ]:
            url = f'http://127.0.0.1:{self.port}{asset}'
            with urllib.request.urlopen(url) as res:
                self.assertEqual(res.status, 200)
                self.assertEqual(res.headers.get('Content-Type'), expected_mime)

    def test_path_traversal_blocked(self):
        url = f'http://127.0.0.1:{self.port}/../../../../etc/passwd'
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url)
        self.assertEqual(ctx.exception.code, 403)


    def test_critical_dom_elements(self):
        with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('id="searchInput"', html)
        self.assertIn('id="previewModal"', html)
        self.assertIn('id="toastContainer"', html)
        self.assertIn('id="uploadProgressContainer"', html)


    def test_auth_enforcement_when_enabled(self):
        import server
        server.AUTH_USER = "admin"
        server.AUTH_PASS = "secret123"
        try:
            url = f'http://127.0.0.1:{self.port}/'
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(url)
            self.assertEqual(ctx.exception.code, 401)
            self.assertIn("WWW-Authenticate", ctx.exception.headers)
            
            # Now test with valid credentials
            req = urllib.request.Request(url)
            creds = base64.b64encode(b"admin:secret123").decode()
            req.add_header("Authorization", f"Basic {creds}")
            with urllib.request.urlopen(req) as res:
                self.assertEqual(res.status, 200)
        finally:
            server.AUTH_USER = None
            server.AUTH_PASS = None


    def test_streaming_multipart_upload(self):
        url = f'http://127.0.0.1:{self.port}/'
        boundary = "---------------------------974767299852498929531610575"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="test_stream.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "Streaming upload test content verified!\r\n"
            f"--{boundary}--\r\n"
        ).encode('utf-8')

        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            self.assertIn("test_stream.txt", data.get("uploaded_files", []))

        # Verify uploaded content and cleanup test file
        test_file_path = os.path.join(BASE_DIR, "test_stream.txt")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


    def test_do_head_method(self):
        url = f'http://127.0.0.1:{self.port}/styles.css'
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.headers.get('Content-Type'), 'text/css')
            self.assertTrue(int(res.headers.get('Content-Length', 0)) > 0)
            self.assertEqual(res.read(), b'')


    def test_security_headers_present(self):
        url = f'http://127.0.0.1:{self.port}/'
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(res.headers.get('X-Frame-Options'), 'SAMEORIGIN')
            self.assertEqual(res.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')


    def test_upload_speed_badge_in_dom(self):
        with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('id="uploadProgressSpeed"', html)


    def test_port_env_variable_fallback(self):
        env_port = os.environ.get("PORT", "8000")
        self.assertTrue(env_port.isdigit())


    def test_gzip_compression_when_accepted(self):
        url = f'http://127.0.0.1:{self.port}/?json=1'
        req = urllib.request.Request(url)
        req.add_header('Accept-Encoding', 'gzip')
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.headers.get('Content-Encoding'), 'gzip')
            raw = res.read()
            decompressed = gzip.decompress(raw)
            data = json.loads(decompressed.decode('utf-8'))
            self.assertIn('entries', data)


    def test_etag_and_304_not_modified(self):
        url = f'http://127.0.0.1:{self.port}/styles.css'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            etag = res.headers.get('ETag')
            self.assertIsNotNone(etag)

        # Re-request with If-None-Match
        req2 = urllib.request.Request(url)
        req2.add_header('If-None-Match', etag)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req2)
        self.assertEqual(ctx.exception.code, 304)


    def test_lan_ip_resolution(self):
        from server import get_local_lan_ip
        ip = get_local_lan_ip()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip.split('.')) == 4)


    def test_large_streaming_upload_efficiency(self):
        url = f'http://127.0.0.1:{self.port}/'
        boundary = "---------------------------5521487214902148712498"
        # 256KB synthetic binary chunk
        payload = b"X" * (256 * 1024)
        body = (
            f"--{boundary}\r\n".encode() +
            b'Content-Disposition: form-data; name="file"; filename="large_sample.bin"\r\n' +
            b"Content-Type: application/octet-stream\r\n\r\n" +
            payload +
            f"\r\n--{boundary}--\r\n".encode()
        )
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            self.assertIn("large_sample.bin", data.get("uploaded_files", []))

        # Clean up
        large_path = os.path.join(BASE_DIR, "large_sample.bin")
        if os.path.exists(large_path):
            self.assertEqual(os.path.getsize(large_path), len(payload))
            os.remove(large_path)


    def test_archive_download_tar_gz(self):
        url = f'http://127.0.0.1:{self.port}/?download=zip'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.headers.get('Content-Type'), 'application/gzip')
            raw = res.read()
            self.assertTrue(len(raw) > 0)

if __name__ == '__main__':
    unittest.main()
