"""Fetcher tests: error paths must return data, never raise, and post_json must not lie."""
import unittest
import urllib.error
from unittest import mock

from exitpath.fetcher import HttpFetcher


class FakeResponse:
    def __init__(self, status=200, body=b"{}"):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class GetTests(unittest.TestCase):
    def test_success_returns_body(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(200, b'{"ok":1}')):
            fetch = HttpFetcher().get("https://example.invalid")
        self.assertEqual((fetch.status, fetch.body, fetch.error), (200, b'{"ok":1}', None))

    def test_http_error_is_data_not_an_exception(self):
        err = urllib.error.HTTPError("https://example.invalid", 404, "Not Found", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            fetch = HttpFetcher().get("https://example.invalid")
        self.assertEqual(fetch.status, 404)
        self.assertIsNone(fetch.error)

    def test_transport_error_is_recorded(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            fetch = HttpFetcher().get("https://example.invalid")
        self.assertEqual(fetch.status, 0)
        self.assertIn("timed out", fetch.error)


class PostTests(unittest.TestCase):
    def test_post_returns_status_and_body(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(200, b'{"result":"0x1"}')):
            status, body = HttpFetcher().post_json("https://example.invalid", {"method": "eth_blockNumber"})
        self.assertEqual((status, body), (200, b'{"result":"0x1"}'))

    def test_post_transport_failure_raises_oserror_for_the_chain_layer(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(OSError):
                HttpFetcher().post_json("https://example.invalid", {"method": "getHealth"})


if __name__ == "__main__":
    unittest.main()
