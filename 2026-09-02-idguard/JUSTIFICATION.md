# Project Justification — idguard (2026-09-02)

## What real problem does this solve?
Lens Intel 2026-09-02 Opportunity 3: the FBI is investigating a service that sold
153M+ US drivers' licenses (KrebsOnSecurity, 219pts). This is the latest in a
multi-week identity-fracture cluster (passport/SSN leak 06-29, dispensary-data
exposures). The recurring failure mode is the same: when a breach dump surfaces,
security teams and affected companies have **no automated way to (a) detect which
high-value identity assets actually leaked** (per-state US drivers'-license numbers,
validatable SSNs, name+DOB+license triples) and **(b) translate that exposure into a
breach-notification plan** (whose data was taken, what state statutes require, what
the affected individuals must do). Enterprises pay $10K+/yr to SpyCloud/Recorded
Future for a subset of this; individuals get nothing.

## Who is the user?
1. Security/abuse responders who receive a leaked dump file and need a fast forensics
   pass before deciding severity + notification scope.
2. Companies that experienced a DLP/breach incident and must triage identity exposure
   and standing up a state-compliant notification.

## Why are existing solutions inadequate?
- BreachSentinel (existing forge-projects build, 06-30) answers "did *my* known email
  leak?" against HIBP/local dumps — it does NOT parse arbitrary dump contents, validate
  SSNs, or detect per-state US drivers'-license formats, and does NOT generate
  notification compliance triage.
- HIBP checks emails only. Enterprise tools are opaque and expensive.
- There is no fully-offline, zero-dependency, CI-able way to classify a raw dump's
  identity-loss severity and emit notification guidance.

## How will we know it's successful?
- `idguard scan <dump>` correctly detects and validates SSNs (rejecting invalid areas/
  groups/ads) and per-state US DL numbers across a representative breadth of states,
  classifies per-record identity-theft severity, and returns a CI-usable exit gate.
- `idguard notify` emits a 50-state breach-notification compliance matrix (window +
  required content + remediation checklist) with accuracy caveats.
- All tests green via pytest, verified against an installed wheel.