"""RED-first end-to-end tests for the CLI exit contract, driven by a fixture fetcher."""
import io
import json
import unittest
from contextlib import redirect_stdout

from exitpath.cli import main


KRAKEN_OK = json.dumps({"page": {"updated_at": "2026-10-31T05:04:17.955Z"}, "components": [
    {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
    {"id": "c1", "name": "USDC (USDC) - Base", "status": "operational", "group": False, "group_id": "g1"},
]}).encode()

KRAKEN_HALTED = json.dumps({"page": {"updated_at": "2026-10-31T05:04:17.955Z"}, "components": [
    {"id": "g1", "name": "Digital Currency Funding", "status": "operational", "group": True, "group_id": None},
    {"id": "c1", "name": "USDC (USDC) - Base", "status": "partial_outage", "group": False, "group_id": "g1"},
]}).encode()

COINBASE_OK = json.dumps({"page": {}, "components": [
    {"id": "g2", "name": "Payment Methods", "status": "operational", "group": True, "group_id": None},
    {"id": "c2", "name": "SEPA Transfers", "status": "operational", "group": False, "group_id": "g2"},
    {"id": "c3", "name": "US Wires", "status": "operational", "group": False, "group_id": "g2"},
]}).encode()

CIRCLE_OK = json.dumps({"page": {}, "components": [
    {"id": "g3", "name": "USDC", "status": "operational", "group": True, "group_id": None},
    {"id": "c4", "name": "USDC - BASE - Redeeming", "status": "operational", "group": False, "group_id": "g3"},
]}).encode()


class FakeFetcher:
    """Stands in for the network. Keyed by URL, returns (Fetch) shapes."""

    def __init__(self, pages, rpc_ok=True):
        self.pages = pages
        self.rpc_ok = rpc_ok

    def get(self, url):
        from exitpath.models import Fetch
        if url in self.pages:
            status, body = self.pages[url]
            return Fetch(status, body, None)
        return Fetch(404, b"not found", None)

    def post_json(self, url, payload):
        if not self.rpc_ok:
            return 200, b'{"jsonrpc":"2.0","error":{"code":-32046,"message":"Cannot fulfill request"},"id":1}'
        if payload.get("method") == "getHealth":
            return 200, b'{"jsonrpc":"2.0","result":"ok","id":1}'
        return 200, b'{"jsonrpc":"2.0","result":"0x10","id":1}'


URLS = {
    "https://status.kraken.com/api/v2/components.json": (200, KRAKEN_OK),
    "https://status.coinbase.com/api/v2/components.json": (200, COINBASE_OK),
    "https://status.circle.com/api/v2/components.json": (200, CIRCLE_OK),
    "https://status.binance.com/api/v2/status.json": (404, b'<html>404</html>'),
}


def run(argv, pages=None, rpc_ok=True):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv, fetcher=FakeFetcher(URLS if pages is None else pages, rpc_ok=rpc_ok))
    return code, buf.getvalue()


class CliTests(unittest.TestCase):
    def test_clean_run_exits_0(self):
        code, out = run(["--json"])
        self.assertEqual(code, 0, out)

    def test_halted_venue_exits_1(self):
        pages = dict(URLS)
        pages["https://status.kraken.com/api/v2/components.json"] = (200, KRAKEN_HALTED)
        code, out = run(["--json"], pages=pages)
        self.assertEqual(code, 1, out)
        report = json.loads(out)
        kraken = [v for v in report["venues"] if v["slug"] == "kraken"][0]
        self.assertEqual(kraken["state"], "halted")
        self.assertIn("Base", kraken["paused_networks"])

    def test_dead_rpc_exits_1(self):
        code, out = run(["--json"], rpc_ok=False)
        self.assertEqual(code, 1, out)

    def test_everything_unmeasurable_exits_2(self):
        code, out = run(["--json"], pages={})
        self.assertEqual(code, 2, out)

    def test_binance_is_reported_unmeasurable_with_its_http_code(self):
        code, out = run(["--json"])
        report = json.loads(out)
        binance = [v for v in report["venues"] if v["slug"] == "binance"][0]
        self.assertEqual(binance["state"], "unmeasurable")
        self.assertEqual(binance["http_code"], 404)

    def test_quiet_prints_nothing(self):
        code, out = run(["--quiet"])
        self.assertEqual((code, out), (0, ""))

    def test_failed_statuspage_venue_forces_exit_2(self):
        pages = {k: v for k, v in URLS.items()
                 if "kraken" not in k}  # kraken now 404s from the fake transport
        code, out = run(["--json"], pages=pages)
        self.assertEqual(code, 2, out)
        kraken = [v for v in json.loads(out)["venues"] if v["slug"] == "kraken"][0]
        self.assertEqual(kraken["state"], "unmeasurable")
        self.assertIn("404", kraken["reason"])

    def test_human_output_mentions_exit(self):
        _, out = run([])
        self.assertIn("exit", out.lower())
        self.assertIn("coverage", out.lower())


if __name__ == "__main__":
    unittest.main()
