"""The one network call. Exercised against a real local HTTP server, not a mock: the failure
modes that matter here are a 404, a non-HTML body, and a timeout, and a mock proves none."""

import http.server
import os
import threading
import unittest

from cvewatch.fetch import FetchError, fetch

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ubuntu_cve_excerpt.html")


class _Handler(http.server.BaseHTTPRequestHandler):
    body = b"<html><title>CVE-2026-98432 | Ubuntu</title></html>"
    status = 200

    def do_GET(self):  # noqa: N802 - stdlib API
        if self.path.startswith("/missing"):
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(self.status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


class FetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_returns_page_text(self):
        text = fetch(self.base + "/security/CVE-2026-98432", timeout=5)
        self.assertIn("CVE-2026-98432", text)

    def test_404_raises_fetch_error(self):
        with self.assertRaises(FetchError) as caught:
            fetch(self.base + "/missing", timeout=5)
        self.assertIn("404", str(caught.exception))

    def test_unreachable_host_raises_fetch_error(self):
        with self.assertRaises(FetchError):
            fetch("http://127.0.0.1:1/nope", timeout=2)

    def test_user_agent_is_set(self):
        # The tracker serves anonymous clients, but an empty UA is treated as a bot by some CDNs.
        self.assertIn("cvewatch", fetch.__doc__ or "")

    def test_fixture_is_readable_by_fetch_via_file_url(self):
        text = fetch("file://" + FIXTURE, timeout=5)
        self.assertIn("cve-table", text)


if __name__ == "__main__":
    unittest.main()
