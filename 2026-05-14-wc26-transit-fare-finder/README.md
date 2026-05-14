# WC26 Fare Finder — NY/NJ Match-Day Transit

A single-page Next.js 15 app that compares **official transit fares vs rideshare/parking** for
fans heading to MetLife Stadium for FIFA World Cup 2026 matches. Built off the May 14, 2026
NY/NJ governors' joint announcement that slashed match-day train fares to **$98** (from $150)
and the official fan shuttle to **$20** (from $80).

## Why

International fans landing at JFK, LGA, EWR or staying in Manhattan, Hoboken or Jersey City
have **no single page** that bundles:

1. The new fare table.
2. Door-to-door times.
3. Last-return-time warnings for late kickoffs.
4. A one-tap `.ics` export for the departure window.
5. Translations for the largest fan languages (EN / ES / PT).

This app does all five. No backend, no DB — the fare table is a typed `const`.

## News source

- **Al Jazeera** — *"World Cup train and shuttle bus ticket prices cut in New York, New Jersey"* —
  published **2026-05-14**.
- URL: <https://www.aljazeera.com/sports/2026/5/14/world-cup-train-and-shuttle-bus-ticket-prices-cut-in-new-york-new-jersey>
- Linked in the footer with publish date.

## How to run

```bash
npm install
npm run dev
# open http://localhost:3000
```

Production build:

```bash
npm run build
npm start
```

Node 20+ recommended.

## What works

- Origin picker: 6 origins (Manhattan, Newark, JFK, LGA, Hoboken, Jersey City).
- Match picker: 8 stub MetLife fixtures spanning the WC26 group stage through the Final.
- Ranked fare options, sorted by total cost (cheapest first).
- Each option card shows:
  - Price (USD) with the original strike-through fare and savings tag where the news cut applies.
  - Door-to-door minutes.
  - Transfer count.
  - Reliability badge (high / medium / low).
  - **Last-return warning** if the match ends after 22:00.
  - **One-tap calendar export** that downloads a valid RFC-5545 `.ics` file —
    opens in Apple Calendar and Google Calendar.
- Language toggle EN / ES / PT swaps all visible strings without a reload.
- Mobile-first responsive at 320 / 768 / 1440.
- POST `/api/estimate` accepts `{ origin, date }` and returns the same ranked options
  as JSON for downstream integrations.
- Footer links the news source with its publish date.

## Architecture

```
app/
  page.tsx              # origin/date picker + results grid (client component)
  layout.tsx            # root metadata + theme
  globals.css           # Tailwind v4 + design tokens
  api/estimate/route.ts # POST {origin,date} -> ranked options
components/
  OriginPicker.tsx
  FareCard.tsx          # price, time, transfers, warning, .ics download
  LastReturnBadge.tsx
  LangToggle.tsx
lib/
  fares.ts              # FARES const — official prices from the news
  routes.ts             # origin -> [option] mapping with times & transfers
  i18n.ts               # en/es/pt dictionaries
  ics.ts                # RFC 5545 .ics builder + departure-stamp math
data/
  matches.json          # WC26 NY/NJ fixture stubs (8 matches)
```

Stack: **next@15**, **react@19** (RC), **tailwindcss@4**, **typescript@5.6**.
Zero secrets. Deploys cleanly on Vercel.

## Known gaps

- **Stub fixtures.** Real WC26 group draw and exact MetLife allocations were not yet
  public at build time; dates and kickoff times are plausible placeholders. Swap
  `data/matches.json` once FIFA publishes final times.
- **Rideshare prices are point estimates.** No live Uber/Lyft API call. Numbers reflect
  typical match-day surge ranges and should be replaced with real-time quotes for
  production use.
- **NJ Transit reliability is generalized.** Service patterns on match day depend on
  final FIFA fixtures; verify against `njtransit.com` before travel.
- **Translations are hand-rolled for the visible UI only.** The static FAQ paragraphs
  are translated but not professionally proofed.
- **No persistence.** Selections do not survive page reloads. Adding `?origin=&date=`
  query-string sync would be a straightforward next step.
- **Lighthouse targets** (Performance ≥ 90, Accessibility ≥ 95, no console errors)
  are designed for and validated against the dev build; CI integration is not
  included.

## License

MIT for the source. Fare and schedule data are public-domain announcements;
verify before travel.
