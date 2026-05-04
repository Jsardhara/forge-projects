## Why
With Iran resuming attacks and the US escorting merchant ships through the Strait of Hormuz (NPR, 2026-05-04), captains, shipping desks, and freight buyers need a single page that says: is the strait passable right now, what's the latest incident, and who's escorting. Currently that signal is scattered across UKMTO advisories, news wires, and AIS trackers.

## What it does
A single-page situational dashboard for the Strait of Hormuz that aggregates public maritime advisories and news into one risk view:
- **Risk gauge** (Green/Amber/Red/Black) derived from a simple rules engine over the latest 24h of incidents.
- **Incident timeline** â€” last 20 events (attacks, escorts, advisories) with source link and timestamp.
- **Escort window** â€” next known US/coalition convoy windows if announced.
- **Affected operators** â€” shipping companies that have publicly suspended transit.
- **Subscribe** â€” email field that posts to a stub (logs to file) so a real ops desk could wire SendGrid later.

Useful to: ship captains, P&I insurers, commodity traders, freight forwarders, journalists.

## Build
Tech: Next.js 15 (App Router) + Tailwind + TypeScript. No DB â€” JSON file as source of truth, server action to refresh.

```
hormuz-transit-advisor/
  app/
    page.tsx              # dashboard (RSC)
    api/subscribe/route.ts# POST handler, appends to subscribers.jsonl
    api/refresh/route.ts  # pulls RSS, rewrites data/incidents.json
  components/
    RiskGauge.tsx         # color-coded status with rationale
    IncidentTimeline.tsx  # vertical timeline, source-linked
    EscortWindow.tsx      # next-convoy card
    OperatorList.tsx      # suspended-transit chips
    SubscribeForm.tsx     # client component
  lib/
    risk.ts               # rules: incidents/24h, severity weights â†’ level
    sources.ts            # RSS feeds (UKMTO, Reuters maritime, NPR)
    fetchFeeds.ts         # parse + dedupe by URL
  data/
    incidents.json        # seeded with 10 real recent items
  tailwind.config.ts
```

Rules engine: count weighted incidents in trailing 24h â€” attack=3, missile-near-miss=2, advisory=1. <2 Green, 2-4 Amber, 5-8 Red, 9+ Black. Rationale string surfaced under gauge.

## Done when
- `pnpm dev` renders dashboard at `/` with seeded data, no console errors.
- Risk gauge color + rationale match rules engine output (unit tested).
- Timeline shows â‰¥10 items, each with working source link and relative timestamp.
- `POST /api/subscribe` with valid email returns 200 and appends to `subscribers.jsonl`; invalid email returns 400.
- `POST /api/refresh` fetches at least one RSS feed and merges new items without duplicating existing URLs.
- Lighthouse mobile â‰¥90 perf, â‰¥95 a11y. Renders cleanly at 375px and 1440px.