# Design Brainstorm: Brows & Beauty by Deepa

## Interface Type
**Landing Page** — Single-page marketing site for a local beauty services business.

## Target User
- **Primary:** Women 25-55 in Wyomissing/Reading/West Berks, PA area
- **Goal:** Find a trusted brow threading/waxing specialist, see services/pricing, book an appointment
- **Context:** Likely found via Google search ("brow threading Wyomissing PA") or Facebook referral
- **Device:** 70%+ mobile — must be flawless on small screens
- **Emotional need:** Trust, warmth, professionalism — not a chain salon, not a random home-based provider

## Reference Analysis
1. **European Wax Center (europeanwaxcenter.com)** — Clean service cards, clear pricing. Borrowing: service grid layout, pricing transparency. Avoiding: corporate/cold feel, generic stock photos.
2. **High-end independent salons on Instagram** — Warm tones, personal branding, before/after focus. Borrowing: personal story element, gallery-first social proof. Avoiding: link-in-bio fragmentation, no real website.
3. **Local competitor Facebook pages** — Most have poor or no websites. Opportunity: a well-designed site is a massive differentiator in this market.
4. **Awwwards salon/beauty sites** — Elegant serif headings, generous whitespace, warm color palettes. Borrowing: Playfair Display + Inter pairing, rose/gold accent strategy.

## Layout Architecture
- **Navigation:** Sticky top nav with logo, smooth-scroll links, mobile hamburger menu
- **Primary action:** "Book Now" phone CTA — visible in nav AND hero AND floating on mobile
- **Content hierarchy:**
  1. Hero (emotional hook + CTA)
  2. Services (what she offers + pricing)
  3. About Deepa (trust + personal connection)
  4. Gallery (visual social proof)
  5. Reviews (testimonials)
  6. Contact (phone, hours, location, form)
  7. Footer (quick links, social, hours)
- **Grid:** Single-column mobile, 2-col tablet, 3-col desktop for services/gallery
- **Whitespace strategy:** Generous padding (py-16/py-24 sections), breathing room between elements
- **Mobile strategy:** Everything stacks single-column, nav becomes hamburger, phone button floats bottom-right

## Design Decisions
- **Color strategy:**
  - Primary: Warm rose/mauve `oklch(0.65 0.12 350)` — feminine, beauty-appropriate, not generic pink
  - Secondary: Warm gold/champagne `oklch(0.85 0.06 80)` — elegance, warmth
  - Base: Warm off-white `oklch(0.98 0.01 80)` — clean, soft, not clinical white
  - Text: Warm charcoal `oklch(0.25 0.01 80)` — readable, not harsh black
  - Accent: Deep plum `oklch(0.45 0.12 330)` — depth, sophistication
- **Typography:**
  - Headings: Playfair Display (elegant serif — beauty industry standard)
  - Body: Inter (clean, readable, modern)
  - Loaded via next/font for zero layout shift
- **Component library:** shadcn/ui (Button, Dialog/Sheet for mobile nav) + custom components
- **Animation:** Subtle fade-in on scroll (IntersectionObserver), hover transitions on cards (150-200ms), no excessive motion
- **Icons:** Lucide React (Scissors, Sparkles, Phone, MapPin, Clock, Star, etc.)

## Component List
- [x] Custom: Navbar (sticky, smooth-scroll, mobile hamburger via Sheet)
- [x] Custom: Hero (full-width gradient bg, headline, subheadline, CTA button)
- [x] Custom: ServiceCard (icon, name, description, price)
- [x] Custom: SectionHeading (serif title + gold underline accent)
- [x] Custom: AboutSection (headshot + bio text, two-column on desktop)
- [x] Custom: GalleryGrid (responsive grid with hover overlay)
- [x] Custom: ReviewCard (stars, quote, reviewer name)
- [x] Custom: ContactSection (phone CTA, hours, location, contact form)
- [x] Custom: Footer (quick links, social, hours, copyright)
- [x] shadcn: Button (primary CTA styling)
- [x] shadcn: Sheet (mobile navigation)
- [x] shadcn: Input, Textarea (contact form)

## Anti-Patterns We're Avoiding
- Generic gradient hero with stock photo illustration — using warm rose gradient with elegant typography
- Everything centered — left-aligned text in sections, only hero centered
- Default Tailwind colors — all colors are custom OKLCH design tokens
- Cards on cards — clean service cards with icons, not nested containers
- No visual hierarchy — clear H1 > H2 > H3 > body scale
- Tiny text — minimum 16px body, 1.6 line height
- Low contrast — all text meets WCAG AA
- No mobile optimization — mobile-first responsive design
- Generic "Lorem Ipsum" — all content is real, warm, professional
- Missing hover/focus states — all interactive elements have proper states
