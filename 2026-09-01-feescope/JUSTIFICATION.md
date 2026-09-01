# Project Justification — feescope (2026-09-01)

**What real problem does this solve?**
On 2026-09-01 the FTC sued Amazon over an alleged "secret ad surcharge scheme" — the
platform charging advertisers billed amounts above the confirmed/verified spend it
reports elsewhere (TechCrunch; Lens daily-intel Op #3). The concrete, hands-on problem
for any advertiser or agency is: *given a billing file of ad-media line items, which
invoices hide surcharges, opaque fee buckets, stacked fees, or excess fee ratios?*
feescope is a deterministic, offline, zero-dependency CLI that answers that in seconds.

**Who's the user?** In-house media buyers, performance marketers, and compliance-aware
agencies reconciling third-party platform invoices against their own verified spend
records. It is a drop-in CI gate (`feescope check`) for an invoices-to-verified-spend
reconciliation pipeline.

**Why are existing solutions inadequate?** Current options are (a) expensive closed
SaaS audit platforms, (b) manual spreadsheet reconciliation with no reproducible
rule-set, or (c) nothing — the majority of mid-size buyers never check for the "secret
surcharge" pattern at all. Within this portfolio, `darkwatch` (consumer dark-pattern
compliance), `costrecon` (AWS cloud billing variance), and `capalarm` (AI plan-cap
spend) all target different domains; none reconcile third-party ad-invoice fee lines
against a trusted `verified` amount. This is a genuine coverage gap.

**How will I know it's successful?** A clean invoice audits to `CLEAR 0/100` with no
findings; an invoice carrying any hidden-surcharge line (billed > verified) audits to a
dominant `FLAG`; and `feescope check` returns a workable exit code (0/1/2) that can gate
a release. All verified by 18 unit tests plus CLI end-to-end runs on the installed
wheel.

**Why this over the other four Lens ops today?** Op #1 (prediction-market analytics /
compliance) is saturated — `predictguard` (06-22) plus the whole Atlas prediction-market
suite already own that space. Op #4 (datasheet/statistical-audit) overlaps the
`contentmark` AI-text-provenance cluster. Op #2 (Mac local-AI fleet mgmt) and Op #5
(GPS jamming monitoring) are SDK/hardware-facing — not a fit for a deterministic daily
CLI build. Op #3 is the only genuinely uncovered, immediately-buildable compliance
vector, and it matches the portfolio's proven zero-dep audit-tool pattern.