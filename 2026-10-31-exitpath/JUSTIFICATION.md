# Project justification — `exitpath`

## The real problem

On 2026-10-30 a compromised Binance employee laptop let a DPRK crew move **$6.3B** out of
the venue inside a **20-minute withdrawal window** (WIRED, TechCrunch, and a 1,732-point HN
thread all converge on the size and the actor). Every article answers the wrong question:
*whether there was a breach*. The question an operator holding funds on a venue actually
needs answered is the opposite one — **can my money still leave, right now, and on which
networks is it stuck?** Withdrawal suspension is the control that converts an accounting
loss into a trapped-user loss: the funds are still "there" in the ledger and cannot move.

## Who the user is

A self-custody-minded holder or a small treasury operator with balances spread over two to
four centralised venues and two chains. They already watch *price*. Nobody offers them
*exit readiness* — a per-venue, per-network statement of whether a withdrawal would clear
this minute, sourced from the venues' own public status pages.

## Why existing solutions are inadequate

- **Price/portfolio trackers** (CoinGecko, portfolio apps) answer "what is it worth", not
  "can I get it out".
- **The venues' own status pages** are the raw material, not a tool: five separate tabs,
  hundreds of components (Kraken publishes 850, Circle 356), and the exit-relevant ones
  are buried as *children* of a parent group ("Digital Currency Funding", "Payment
  Methods", "USDC - … - Redeeming"). Reading them by eye at 3am is how a halt is missed.
- **Uptime monitors** check HTTP 200. This project measured today that **HTTP 200 is not
  health**: `cloudflare-eth.com` returns `200` with a JSON-RPC body of
  `{"error":{"code":-32046,"message":"Cannot fulfill request"}}`. A 200-only monitor calls
  that chain healthy.
- **Chain explorers** show chain liveness, not whether the *issuer* or the *venue* will let
  value cross the boundary.

## The uncovered slice, and only that slice

A read-only, keyless, stdlib-only CLI that normalises public status signals into one
**exit contract**: per venue — withdrawals open / degraded / halted, with the exact
components that say so and the networks that are paused; per chain — an RPC that actually
returned a block height, not merely a 200. Anything that would need authentication is
declared out of scope and reported as **unmeasurable**, never as operational.

Not a news monitor, not a portfolio tracker, not a trading tool, and it never holds or
prints a credential. Coverage is printed honestly rather than implied: the build ships
what it measured as reachable, and names what it could not.
