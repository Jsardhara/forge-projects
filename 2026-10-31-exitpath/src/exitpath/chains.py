"""Chain layer: prove a chain can actually be read, not that it answered HTTP 200.

Measured 2026-10-31 against real public endpoints:
  cloudflare-eth.com  -> HTTP 200 + {"error":{"code":-32046,"message":"Cannot fulfill request"}}
  ethereum-rpc.publicnode.com -> HTTP 200 + {"result":"0x1917903"}
So the health predicate is "did a block number / ok result come back", never the status code.
"""
import json
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .models import ChainHealth

ETH_BLOCK = "eth_blockNumber"
HEALTH = "getHealth"


@dataclass(frozen=True)
class Chain:
    chain: str
    endpoint: str
    method: str = ETH_BLOCK
    note: str = ""


CHAINS: Tuple[Chain, ...] = (
    Chain("ethereum", "https://ethereum-rpc.publicnode.com", ETH_BLOCK,
          "cloudflare-eth.com answers 200 with a JSON-RPC error; not a health source"),
    Chain("base", "https://base-rpc.publicnode.com", ETH_BLOCK),
    Chain("solana", "https://solana-rpc.publicnode.com", HEALTH),
)


def parse_rpc(method: str, body) -> Tuple[bool, Optional[int], Optional[str]]:
    """(ok, block_height, error). Never raises: a broken feed is a finding, not a crash."""
    try:
        text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
        doc = json.loads(text)
    except (ValueError, AttributeError):
        return False, None, "non-JSON response body"
    if not isinstance(doc, dict):
        return False, None, "unexpected JSON document shape"

    err = doc.get("error")
    if err:
        msg = err.get("message") if isinstance(err, dict) else str(err)
        return False, None, "JSON-RPC error: %s" % (msg or "unspecified")

    result = doc.get("result")
    if method == HEALTH:
        if result == "ok":
            return True, None, None
        return False, None, "node health: %s" % (result,)

    if not isinstance(result, str) or not result.startswith("0x"):
        return False, None, "missing hex block number"
    try:
        return True, int(result, 16), None
    except ValueError:
        return False, None, "malformed hex block number %r" % (result,)


def probe(chain: Chain, post, clock=time.monotonic) -> ChainHealth:
    """post(url, payload) -> (status, body). Latency measured around the single call."""
    t0 = clock()
    try:
        status, body = post(chain.endpoint, {"jsonrpc": "2.0", "id": 1, "method": chain.method, "params": []})
    except Exception as exc:  # noqa: BLE001 - transport failure is a finding
        return ChainHealth(chain.chain, chain.endpoint, False, None, None,
                           "%s: %s" % (type(exc).__name__, exc))
    latency = round((clock() - t0) * 1000.0, 1)
    ok, height, err = parse_rpc(chain.method, body)
    if status != 200 and not ok:
        err = "HTTP %s" % status
    return ChainHealth(chain.chain, chain.endpoint, ok, height, latency, err)


def collect_chains(post, chains: Tuple[Chain, ...] = CHAINS, clock=time.monotonic) -> Tuple[ChainHealth, ...]:
    return tuple(probe(c, post, clock) for c in chains)
