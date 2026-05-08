## Why

A hantavirus outbreak on a cruise ship bound for the Canary Islands plus a suspected case on Tristan da Cunha shows how fast zoonotic clusters spread across borders. Travelers, port workers, and clinicians need a single plain-language page that explains symptoms, transmission, current case clusters, and what to do if exposed â€” not buried in 12 news articles.

## What it does

A single-page web app that gives anyone:

- Plain-English **symptom checker** (fever + muscle aches + recent rodent/cruise exposure â†’ triage advice)
- **Live case map** of confirmed and suspected hantavirus clusters (cruise ship, Canary Islands, Tristan da Cunha, UK)
- **Exposure timeline** â€” "were you on X ship between these dates?"
- **What to do next** card: when to seek care, what to tell a clinician (HPS vs HFRS), CDC/WHO source links
- Shareable URL so a worried traveler can send it to family

No accounts. No tracking. Static-first, fast on mobile, works on hotel wifi.

## Build

Stack: Next.js 15 (App Router) + Tailwind + TypeScript. Static export, deployable to Vercel free tier. No backend.

```
app/
  layout.tsx          # base shell, OG tags
  page.tsx            # landing â€” outbreak summary + CTA
  checker/page.tsx    # 4-question symptom + exposure flow
  map/page.tsx        # case cluster map
  guide/page.tsx      # what-to-do + clinician script
components/
  SymptomFlow.tsx     # client-side decision tree
  ClusterMap.tsx      # react-leaflet, static GeoJSON
  ExposureCheck.tsx   # date+ship matcher
  SourceCard.tsx      # cited link card
data/
  clusters.json       # {location, lat, lng, status, source_url, updated}
  ships.json          # {name, route, dates, status}
  symptoms.json       # decision tree config
lib/
  triage.ts           # pure function: answers â†’ advice tier
```

Key libs: `react-leaflet` (map), `zod` (data validation), no DB. All data in `/data/*.json`, editable by hand, refreshed manually as news updates.

## Done when

- Loads under 2s on 4G, Lighthouse perf â‰¥ 90
- Symptom flow returns advice in â‰¤ 4 clicks
- Map shows â‰¥ 4 cluster pins with source citations
- Exposure check flags the named cruise ship by date range
- Every medical claim links to CDC, WHO, or national health authority
- Mobile-first; works keyboard-only; passes axe accessibility scan
- Clear disclaimer: informational, not medical advice