# Design Brainstorm: RegShield

## Interface Type
Dashboard / SaaS Tool — compliance monitoring with real-time alerts

## Target User
CISOs, legal teams, and AI platform engineers at companies using multiple AI vendors. They need to know which AI models are restricted in which jurisdictions and get alerts when regulatory status changes.

## Reference Analysis
1. **Drata** — Clean compliance dashboard, trust center pattern. Borrowing: status overview cards, framework mapping tables.
2. **Vercel Dashboard** — Clean deployment status pattern. Borrowing: green/yellow/red status indicators, real-time status badges.
3. **Linear** — Issue tracking with priority. Borrowing: alert severity levels, filterable tables.
4. **Avoiding**: Generic gradient heroes, card-on-card nesting, centered-everything layouts.

## Layout Architecture
- Navigation: Top bar with logo, nav links, org selector
- Primary action: "Check Model Availability" — a search bar that checks if a model is available in a country
- Grid: 12-col, main content 8-col, sidebar 4-col for alerts/status
- Mobile: Sidebar collapses to bottom sheet, table becomes cards

## Design Decisions
- Color strategy: Zinc base + amber for warnings, emerald for compliant, red for restricted
- Typography: Inter for body, JetBrains Mono for model names/codes
- Component library: shadcn/ui (if building React frontend) or Jinja2 templates with Tailwind
- Animation: Subtle fade-in for status changes, pulse for active alerts

## Component List
- [x] Model Registry Table — sortable, filterable table of all tracked models
- [x] Compliance Checker — search form: model + country + use case → status
- [x] Alert Banner — real-time notifications for regulatory changes
- [x] Status Badge — green/yellow/red indicator per model per jurisdiction
- [x] Audit Log — chronological record of compliance checks

## Anti-Patterns We're Avoiding
- No gradient hero sections
- No fake data or placeholder compliance scores
- No cards inside cards inside cards
- No default Tailwind colors (blue-500, gray-200)
- No centered everything — left-aligned content with clear hierarchy
