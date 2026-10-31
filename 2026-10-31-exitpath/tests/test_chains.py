"""RED-first tests for chain RPC health: a 200 is not a healthy chain."""
import unittest

from exitpath.chains import parse_rpc, probe, Chain


class ParseTests(unittest.TestCase):
    def test_hex_block_number_is_parsed(self):
        ok, height, err = parse_rpc("eth_blockNumber", b'{"jsonrpc":"2.0","result":"0x1917903","id":1}')
        self.assertTrue(ok)
        self.assertEqual(height, 26310915)
        self.assertIsNone(err)

    def test_jsonrpc_error_envelope_is_not_healthy(self):
        # The real cloudflare-eth.com body measured 2026-10-31: HTTP 200 + this error.
        body = b'{"jsonrpc":"2.0","error":{"code":-32046,"message":"Cannot fulfill request"},"id":1}'
        ok, height, err = parse_rpc("eth_blockNumber", body)
        self.assertFalse(ok)
        self.assertIsNone(height)
        self.assertIn("Cannot fulfill request", err)

    def test_gethealth_ok(self):
        ok, _, err = parse_rpc("getHealth", b'{"jsonrpc":"2.0","result":"ok","id":1}')
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_gethealth_behind_is_not_ok(self):
        ok, _, err = parse_rpc("getHealth", b'{"jsonrpc":"2.0","result":"behind","id":1}')
        self.assertFalse(ok)
        self.assertIn("behind", err)

    def test_non_json_body_is_error_not_crash(self):
        ok, _, err = parse_rpc("eth_blockNumber", b"<html>404</html>")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_malformed_hex_is_error(self):
        ok, _, err = parse_rpc("eth_blockNumber", b'{"result":"zzz"}')
        self.assertFalse(ok)
        self.assertTrue(err)


class ProbeTests(unittest.TestCase):
    def test_probe_uses_injected_post(self):
        chain = Chain("ethereum", "https://example.invalid", "eth_blockNumber")
        seen = {}

        def post(url, payload):
            seen["url"] = url
            seen["method"] = payload["method"]
            return 200, b'{"result":"0x10"}'

        health = probe(chain, post, clock=lambda: 0.0)
        self.assertTrue(health.ok)
        self.assertEqual(health.block_height, 16)
        self.assertEqual(seen["url"], "https://example.invalid")
        self.assertEqual(seen["method"], "eth_blockNumber")

    def test_transport_failure_is_not_ok(self):
        def boom(url, payload):
            raise TimeoutError("timed out")

        health = probe(Chain("base", "https://example.invalid", "eth_blockNumber"), boom, clock=lambda: 0.0)
        self.assertFalse(health.ok)
        self.assertIn("timed out", health.error)


if __name__ == "__main__":
    unittest.main()
