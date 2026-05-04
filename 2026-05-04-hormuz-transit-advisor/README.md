# Hormuz Transit Advisor

Single-page situational dashboard for the Strait of Hormuz. Aggregates public
maritime advisories and news into one risk view so captains, P&I insurers,
freight buyers, and journalists can answer one question fast: *is the strait
passable right now?*

Inspired by [NPR — Iran war updates, 2026-05-04](https://www.npr.org/2026/05/04/nx-s1-5810508/iran-war-updates).

---

## Purpose

The signal that matters to anyone routing tonnage through Hormuz today is
scattered across UKMTO advisories, Reuters wires, NPR/AP world coverage, and
private AIS trackers. This project consolidates the public portion of that
signal into:

- A **risk gauge** (Green / Amber / Red / Black) driven by a transparent rules
  engine over the last 24 hours of incidents.
- A **timeline** of the most recent 20 events — attacks, near-misses,
  advisories, escorts — each linking back to its source.
- The **next known escort windows** announced by IMSCC / CENTCOM / coalition
  navies.
- The **operators** that have publicly suspended, rerouted, or are monitoring
  Hormuz transit.
- A **subscribe** stub that logs an email so an ops desk could wire SendGrid
  later without changing the UI.

This is not investment, security, or routing advice. Always verify with UKMTO
Bahrain ops cell, your flag-state, and your insurer before transit decisions.

## News source

Editorial trigger: NPR, *Iran war updates*, 2026-05-04
(https://www.npr.org/2026/05/04/nx-s1-5810508/iran-war-updates).

The seeded incident dataset cites Reuters, UKMTO, CENTCOM, MARAD, AP, NHK,
Bloomberg, Lloyd's List, and US Navy press releases. The live `/api/refresh`
route pulls RSS from UKMTO, Reuters Energy, and NPR World; non-Hormuz items
are filtered by a keyword list in `lib/sources.ts`.

## Tech stack

- **Next.js 15** (App Router, RSC, route handlers)
- **TypeScript** strict mode
- **Tailwind CSS** for styling
- **fast-xml-parser** for RSS parsing
- **Vitest** for unit tests
- No database. JSON files in `data/` are the source of truth.

## How to run

```bash
# install (npm, pnpm, or yarn — pnpm recommended)
pnpm install

# dev server
pnpm dev
# → open http://localhost:3000

# unit tests for the rules engine
pnpm test

# production build
pnpm build && pnpm start
```

### Refreshing live data

```bash
# pulls UKMTO + Reuters + NPR feeds, dedupes by source URL,
# merges into data/incidents.json
curl -X POST http://localhost:3000/api/refresh
```

The refresh endpoint is intentionally idempotent — running it twice does
not create duplicates because the merge keys on `sourceUrl`.

### Subscribing

```bash
curl -X POST http://localhost:3000/api/subscribe \
  -H 'content-type: application/json' \
  -d '{"email":"captain@example.com"}'
# → 200 { "ok": true }, appends to data/subscribers.jsonl
# Invalid email returns 400.
```

`subscribers.jsonl` is git-ignored.

## Risk rules engine

Lives in `lib/risk.ts`. Each incident kind contributes a fixed weight:

| Kind                | Weight |
|---------------------|--------|
| `attack`            | 3      |
| `missile-near-miss` | 2      |
| `advisory`          | 1      |
| `escort`            | 0      |

Sum the weighted incidents whose `timestamp` falls within the trailing 24
hours, then map to a band:

| Score | Level | Meaning                           |
|-------|-------|-----------------------------------|
| 0–1   | GREEN | Routine — no significant disruption |
| 2–4   | AMBER | Elevated — exercise caution         |
| 5–8   | RED   | High — active threats reported      |
| 9+    | BLACK | Severe — transit not advised        |

The rationale string under the gauge surfaces *why* the level was chosen
("1 attack, 1 near-miss, 2 advisories in last 24h → weighted score 7 (RED).").

Unit tests in `lib/risk.test.ts` cover every band edge and the windowing.

## Project layout

```
app/
  layout.tsx            # root shell, dark editorial theme
  page.tsx              # dashboard (RSC) — composes all panels
  globals.css           # Tailwind + design tokens
  api/subscribe/route.ts # POST handler → subscribers.jsonl
  api/refresh/route.ts   # POST/GET → re-pull RSS, merge, save
components/
  RiskGauge.tsx
  IncidentTimeline.tsx
  EscortWindow.tsx
  OperatorList.tsx
  SubscribeForm.tsx     # client component
lib/
  risk.ts               # rules engine
  risk.test.ts          # vitest spec
  sources.ts            # RSS feed list + keyword filter
  fetchFeeds.ts         # parse + classify + merge
  dataStore.ts          # JSON read/write helpers
  format.ts             # relative-time formatting
  types.ts
data/
  incidents.json        # seeded with 12 illustrative recent items
  operators.json
  escorts.json
```

## What works

- Dashboard renders at `/` from seeded JSON with no console errors.
- Risk gauge color and rationale match the rules engine output, verified by
  unit tests covering every band (Green / Amber / Red / Black) and the
  24-hour window cutoff.
- Timeline shows ≥10 source-linked items with relative timestamps and
  per-kind color coding.
- Escort window panel displays upcoming announced convoys.
- Operator list groups by status (suspended → rerouted → monitoring) and
  links to each operator's public statement.
- `POST /api/subscribe` validates email shape, returns 200/400, appends a
  JSON line to `data/subscribers.jsonl`.
- `POST /api/refresh` fetches each RSS source, classifies item kind by
  keyword, filters by Hormuz-relevance, dedupes by `sourceUrl`, and persists.
- Responsive at 375 px and 1440 px. Reduced-motion respected.

## Known gaps

- **No DB.** Suitable for single-node MVP; concurrent refreshes can race the
  JSON file. Swap `dataStore.ts` for SQLite/Postgres before production.
- **RSS feed URLs are best-effort.** UKMTO does not publish a stable public
  RSS; the URL in `lib/sources.ts` is the documented endpoint and may need
  an authenticated alternative or scrape fallback.
- **Severity classification is keyword-based** in `lib/sources.ts::classifyKind`.
  False positives are possible. Production would benefit from an LLM
  classifier or human-in-the-loop review queue.
- **Subscribe stub only logs.** No double-opt-in, no SendGrid wiring, no
  unsubscribe flow.
- **No authentication** on `/api/refresh`. Add a shared-secret header before
  exposing the endpoint publicly.
- **Timestamps are server-side UTC.** No per-user timezone yet.
- **Escort windows are static.** Real source would be UKMTO + 5th Fleet
  daily ops summaries, which are not machine-readable today.
- Lighthouse targets (≥90 mobile perf, ≥95 a11y) are designed for, not
  measured in CI. Run locally with `lighthouse http://localhost:3000` after
  `pnpm build && pnpm start`.

## License

MIT — see source. Data sources retain their own copyright; this project
links rather than re-publishes.
