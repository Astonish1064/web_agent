import unittest
import os
import shutil
import urllib.request
from src.agent.environments.server import LocalWebServer

class TestLocalWebServer(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/web_server_test"
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "index.html"), "w") as f:
            f.write("<html><body>Test Success</body></html>")
        self.server = LocalWebServer(self.test_dir)

    def tearDown(self):
        self.server.stop()
        shutil.rmtree(self.test_dir)

    def test_server_starts_and_serves(self):
        self.server.start()
        self.assertTrue(self.server.is_running)
        self.assertIsNotNone(self.server.port)
        
        # Try to fetch index.html
        url = f"http://localhost:{self.server.port}/index.html"
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            self.assertEqual(content, "<html><body>Test Success</body></html>")

if __name__ == "__main__":
    unittest.main()
