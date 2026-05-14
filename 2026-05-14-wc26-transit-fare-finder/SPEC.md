## Why
NY/NJ just slashed World Cup 2026 transit fares (train $98 from $150, shuttle $20 from $80). Fans arriving from dozens of countries need one clear page to compare official transit options vs rideshare/parking for each match-day venue. No single site bundles the new fares with venue routing yet.

## What it does
Match-day fare comparator for MetLife Stadium and surrounding NY/NJ venues. User picks origin (Manhattan, Newark, JFK, LGA, Hoboken, Jersey City) + match date. App returns ranked options: NJ Transit train, official shuttle bus, PATH+walk, rideshare estimate, drive+park. Each card shows price, door-to-door time, transfers, last-return-time warning, and a one-tap "add to calendar" for departure. Includes a static FAQ pulled from the fare-cut announcement and a multilingual toggle (EN/ES/PT) since the audience is international.

## Build
Next.js 15 App Router + Tailwind + shadcn/ui. No database â€” fare table is a typed const.

```
app/
  page.tsx              # origin/date picker + results grid
  layout.tsx            # header, lang switcher
  api/estimate/route.ts # POST {origin,date} -> ranked options
components/
  OriginPicker.tsx
  FareCard.tsx          # price, time, transfers, warning
  LastReturnBadge.tsx
  LangToggle.tsx
lib/
  fares.ts              # const FARES: official prices from news
  routes.ts              # origin -> [option] mapping w/ times
  i18n.ts               # en/es/pt strings
  ics.ts                # build .ics for calendar export
data/
  matches.json          # WC26 NY/NJ fixture stubs
```

Stack pinned: next@15, react@19, tailwindcss@4, typescript@5.6, date-fns@4. Deploy: Vercel. Zero secrets.

## Done when
- Loads under 1.5s on 4G, LCP < 2.5s, mobile-first responsive at 320/768/1440.
- User selects any of 6 origins + any of 8 stub match dates and sees â‰¥3 ranked fare options sorted by total cost.
- Each option shows: price (USD), door-to-door minutes, transfer count, last-return warning if match ends after 22:00.
- Calendar export downloads a valid .ics file that opens in Apple Calendar and Google Calendar.
- Language toggle swaps EN/ES/PT for all visible strings without reload.
- Lighthouse: Performance â‰¥90, Accessibility â‰¥95, no console errors.
- News source linked in footer with publish date.