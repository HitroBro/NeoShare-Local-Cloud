import os
import unittest
import urllib.request
import urllib.error
import json
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

if __name__ == '__main__':
    unittest.main()
