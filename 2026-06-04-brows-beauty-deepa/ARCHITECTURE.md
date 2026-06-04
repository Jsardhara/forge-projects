# Architecture: Brows & Beauty by Deepa

## Tech Stack
- **Framework:** Next.js 14 (App Router) — `npx create-next-app@latest` with TypeScript + Tailwind
- **Styling:** Tailwind CSS with custom OKLCH design tokens in `globals.css`
- **UI Components:** shadcn/ui (Button, Sheet, Input, Textarea, Dialog)
- **Icons:** Lucide React
- **Fonts:** next/font — Playfair Display (headings) + Inter (body)
- **Deployment:** Vercel (connected to GitHub, auto-deploy on push)

## Project Structure
```
2026-06-04-brows-beauty-deepa/
├── DESIGN.md                    # Design brainstorm (completed)
├── ARCHITECTURE.md              # This file
├── README.md                    # Setup + deployment instructions
├── .gitignore                   # Next.js standard
├── next.config.ts               # Next.js config
├── package.json                 # Dependencies
├── tailwind.config.ts           # Custom design tokens
├── tsconfig.json                # TypeScript config
├── postcss.config.mjs           # PostCSS for Tailwind
├── components.json              # shadcn/ui config
├── app/
│   ├── layout.tsx               # Root layout (fonts, metadata)
│   ├── page.tsx                 # Single-page site (all sections)
│   └── globals.css              # Tailwind imports + design tokens
├── components/
│   ├── ui/                      # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── sheet.tsx
│   │   ├── input.tsx
│   │   └── textarea.tsx
│   ├── Navbar.tsx               # Sticky nav + mobile hamburger
│   ├── Hero.tsx                 # Hero section with CTA
│   ├── Services.tsx             # Service cards grid
│   ├── About.tsx                # About Deepa section
│   ├── Gallery.tsx              # Before/after photo grid
│   ├── Reviews.tsx              # Testimonials
│   ├── Contact.tsx              # Contact form + info
│   └── Footer.tsx               # Footer
└── public/
    └── (placeholder images referenced via placehold.co URLs)
```

## Design Token System
All colors defined as CSS variables in `globals.css` using OKLCH:
```css
:root {
  --background: oklch(0.98 0.01 80);      /* warm off-white */
  --foreground: oklch(0.25 0.01 80);       /* warm charcoal */
  --primary: oklch(0.65 0.12 350);         /* warm rose/mauve */
  --primary-foreground: oklch(0.98 0.01 80);
  --secondary: oklch(0.85 0.06 80);        /* warm gold/champagne */
  --secondary-foreground: oklch(0.25 0.01 80);
  --muted: oklch(0.96 0.01 80);            /* light warm gray */
  --muted-foreground: oklch(0.50 0.01 80); /* medium warm gray */
  --accent: oklch(0.45 0.12 330);          /* deep plum */
  --accent-foreground: oklch(0.98 0.01 80);
  --border: oklch(0.90 0.01 80);
  --radius: 0.75rem;
}
```

## Key Design Decisions
1. **Single-page architecture** — All sections in `page.tsx`, smooth-scroll via anchor links. Simpler for a small business site, faster to load.
2. **Placeholder images** — Using `https://placehold.co/` with labeled alt text. Client replaces later.
3. **No external CMS** — Static content in components. Client can edit via GitHub PR or we can add Sanity/Strapi later.
4. **Form handling** — Contact form uses Formspree or similar (no backend needed for MVP).
5. **SEO** — Metadata in `layout.tsx`, semantic HTML, local business JSON-LD schema.
6. **Performance** — next/image for optimization, lazy loading, minimal JS bundle.

## Section Order
1. Navbar (sticky)
2. Hero — Warm gradient, headline, CTA
3. Services — 6 service cards with icons, descriptions, prices
4. About — Deepa's photo + bio
5. Gallery — 6-item grid with hover overlay
6. Reviews — 5 testimonial cards
7. Contact — Phone, hours, location, contact form
8. footer — Links, social, hours, copyright

## Deployment Plan
1. Scaffold Next.js project in project folder
2. Install shadcn/ui + dependencies
3. Build all sections
4. Test locally (`next dev`)
5. Build production (`next build`)
6. Push to GitHub (auto-deploys to Vercel)
7. Connect custom domain (client provides later)
