# exitpath

**Can funds actually leave?** A read-only, keyless, stdlib-only checker that reports
*exit readiness* per venue and per chain — withdrawals open / degraded / halted, which
networks are paused, and whether an RPC actually returned a block.

It answers the question the headlines do not. On 2026-10-30 a DPRK crew moved $6.3B out of
Binance inside a 20-minute withdrawal window (WIRED · TechCrunch · HN). Every article
answers "was there a breach". An operator holding funds needs the opposite: **if I tried to
withdraw right now, would it clear, and on which networks is it stuck?**

## What it measures (and what it refuses to)

| Layer | Source | Method |
|---|---|---|
| Venues — Kraken, Coinbase | `status.<venue>.com/api/v2/components.json` | statuspage.io components, filtered to the funding/payment subset |
| Issuer — Circle (USDC / EURC) | `status.circle.com/api/v2/components.json` | per-chain `- Redeeming` rows + CCTP / USDC Bridge groups |
| Chains — Ethereum, Base, Solana | public JSON-RPC | `eth_blockNumber` / `getHealth` — **a result, not an HTTP 200** |
| Binance | none exists (probed 404) | reported **unmeasurable**, never "operational" |

No API keys, no account endpoints, no signing, no orders, no credentials. If a measurement
would need auth, it is out of scope and reported as unmeasurable.

## Install

None. Python 3.8+ standard library only, no third-party dependencies.

```bash
cd 2026-10-31-exitpath
PYTHONPATH=src python3 -m exitpath            # human report
PYTHONPATH=src python3 -m exitpath --json     # machine rollup
PYTHONPATH=src python3 -m exitpath --venues kraken,usdc --no-chains
```

Exit contract (CI-friendly):

| code | meaning |
|---|---|
| `0` | clean — every measured exit path is open |
| `1` | findings — at least one venue/chain is degraded or halted |
| `2` | unmeasurable — nothing contradicted, but a required signal could not be read |

A real halt outranks "unmeasurable": finding beats exit 2, so a blocked exit is never hidden
behind a failed fetch. A venue with *no public signal at all* (Binance) is counted in
`coverage` as uncovered but does not pin the exit code — otherwise the gate would be
permanently red and get ignored.

## Example (live, 2026-10-31T06:24Z)

```
VENUES / ISSUERS
  kraken     degraded      degraded on BNB Chain, Ethereum | Digital Currency Funding (group) degraded; ...
  coinbase   open          20 exit components checked, all open | venue page: minor -- Partially Degraded Service
  usdc       halted        Circle Cross-Chain Transfer Protocol (group) halted; CRONOS - Cross-Chain Minting and Burning halted
  binance    unmeasurable  no public status JSON (HTTP 404) -- withdrawals not measurable from a public signal

CHAINS (a 200 is not health; a block height is)
  ethereum   healthy   block 26310941 (101.2ms)
  base       healthy   block 53319307 (129.2ms)
  solana     healthy   healthy (100.4ms)

coverage: venues 3/4 measured, chains 3/3 healthy
exit: 1 -- findings -- at least one exit path is degraded or halted
```

That Coinbase line is the tool doing its job: the venue-wide page says *minor* while the
exit slice is entirely `operational`. Reporting only "open" would have been a clean bill of
health issued during a degraded venue.

## Design decisions worth knowing

- **HTTP 200 is not health.** `cloudflare-eth.com` returns `200` with
  `{"error":{"code":-32046,"message":"Cannot fulfill request"}}`. Any monitor that trusts
  the status code calls that chain healthy. `parse_rpc` requires a block number / `ok`.
- **Only non-open components are listed.** Kraken publishes 850 components — 733 of them are
  per-asset funding rows. The tool counts what it checked (`components_checked`) and reports
  only the rows that are not `operational`, otherwise the two that matter are invisible.
- **Parent group state counts.** Kraken's `Digital Currency Funding` parent was
  `degraded_performance` while every child read `operational`. Reading only children reports
  a clean venue during a real funding degradation.
- **Networks are deduped.** The same chain appears once per asset; the output lists it once.
- **`observed_at` comes from the status page**, not the local clock — you can see how stale
  a venue's own self-report is.
- **The venue-wide indicator is fetched separately** (`api/v2/status.json`). Components alone
  never carry it — verified: none of the three payloads has a top-level `status` key. Two GETs
  per venue, and the second one failing changes nothing except a missing note.

## Limits (stated, not implied)

- Coverage is 3 of 4 venues measured. Binance publishes no public status JSON (two separate
  404s, probed) — for Binance the honest answer is "cannot measure read-only", and the tool
  says exactly that rather than guessing.
- The status page is the venue's *self-report*. A venue that lies, or that has suspended
  withdrawals without updating its status page, is not detectable here.
- Component selection is a declared registry (`src/exitpath/venues.py`), not NLP. Adding a
  venue means one `Venue(...)` entry with its group names; if the venue renames a component,
  the venue becomes `unmeasurable` (loud), not silently `open`.
- Chain health is one public endpoint per chain. It proves the chain is readable, not that a
  bridge or a specific contract works.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests      # 67 tests
```

`tests/fixtures/real/` holds the three live statuspage payloads recorded on 2026-10-31
(850 / 175 / 356 components). The suite tests those, not just hand-written fixtures —
self-authored fixtures only prove the code is consistent with itself.

## Scope

Not a news monitor, not a portfolio/price tracker, not a trading or order tool, and it never
polls faster than a human would: run it on demand or from a cron, cache-friendly by design
(one GET per venue per run).
