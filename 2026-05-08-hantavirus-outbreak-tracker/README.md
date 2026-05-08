# Hantavirus Outbreak Tracker (May 2026)

A single-page web app that explains the May 2026 hantavirus outbreak in plain English: symptoms, exposure check, case map, and what to do next. Static-first, no backend, no tracking, no accounts.

## Purpose

A hantavirus cluster on the **MV Atlantic Voyager** (cruise ship bound for the Canary Islands) plus a suspected case on **Tristan da Cunha** is moving fast across borders. Travelers, port workers, and clinicians need a single, trustworthy page that answers: *Am I at risk? What should I do? Where are the cases?* — without reading 12 news articles.

## News source

Built on reporting from:

- **Al Jazeera, 8 May 2026** — [Hantavirus cases rise on cruise ship as UK tracks nationals](https://www.aljazeera.com/news/2026/5/8/hantavirus-cases-rise-on-cruise-ship-as-uk-tracks-nationals)
- Cross-referenced with CDC, WHO, and UKHSA. Every medical claim links out.

## How to run

Requires Node 18.17+ (or 20+) and a package manager (`npm`, `pnpm`, or `yarn`).

```bash
npm install
npm run dev
# open http://localhost:3000
```

Production static export:

```bash
npm run build
# output is in ./out — drop on Vercel, Netlify, S3, or any static host
```

## What works

- **Landing page** with outbreak summary, plain-language explainer, cluster table.
- **Symptom checker** — 4-question decision tree at `/checker/`. Returns a triage tier (emergency / urgent / monitor / reassure) plus a clinician script. Pure function in `lib/triage.ts`.
- **Exposure check** — date + ship name → flags overlap with known affected voyages.
- **Cluster map** at `/map/` — react-leaflet pins for MV Atlantic Voyager, Tenerife, Tristan da Cunha, Funchal, UK; each pin links to its source.
- **Action guide** at `/guide/` — step-by-step what to do, HPS vs HFRS reference, clinician script, source cards.
- Mobile-first, keyboard-accessible, respects `prefers-reduced-motion`.
- Static export (`output: 'export'`) — deployable to Vercel free tier, Netlify, GitHub Pages.
- All data hand-editable in `data/clusters.json`, `data/ships.json`, `data/symptoms.json` — no DB, no API.

## File layout

```
app/
  layout.tsx          base shell, OG tags, footer disclaimer
  page.tsx            landing
  checker/page.tsx    symptom + exposure flow
  map/page.tsx        leaflet map + cluster details
  guide/page.tsx      what to do + clinician script + sources
components/
  SymptomFlow.tsx     decision tree, client-side
  ClusterMap.tsx      react-leaflet (dynamic import — no SSR)
  ExposureCheck.tsx   date + ship matcher
  SourceCard.tsx      cited link card
data/
  clusters.json       cluster pins
  ships.json          affected voyages
  symptoms.json       decision-tree config
lib/
  triage.ts           pure function: answers → advice tier
  schemas.ts          zod schemas for data files
```

## Updating the data

Outbreaks move. To refresh:

1. Edit `data/clusters.json` — add/update pins. Each needs a `source_url` to a primary source (CDC, WHO, national health authority, or major news).
2. Edit `data/ships.json` if a new voyage is implicated.
3. Edit `data/symptoms.json` only if WHO/CDC change the case definition.
4. `npm run build` and redeploy.

Schemas in `lib/schemas.ts` (zod) describe the expected shape.

## Known gaps

- **Data is hand-curated, not live.** A daily scrape from WHO Disease Outbreak News + UKHSA RSS would close this loop.
- **No i18n.** English only. Spanish and Portuguese translations would matter for port workers in Tenerife and Funchal.
- **Map tiles depend on OpenStreetMap CDN.** Offline scenarios degrade.
- **Symptom flow is rule-based, not validated.** Conservative by design (errs toward "see a clinician"). Clinician script written from CDC / WHO public guidance — should be reviewed by an infectious-disease clinician before any wider release.
- **No analytics, intentionally.** Means we don't know if anyone is using it.
- **No social-share images** generated — relies on default OG meta.
- **Accessibility passes manual axe scan**, no automated CI gate yet.

## Disclaimer

Informational only. Not medical advice. Do not delay seeking care because a web page told you your tier was "monitor." If in doubt, call a clinician.

## License

MIT — fork, translate, and reuse. Attribution to cited sources required because they did the journalism and the public-health work.
