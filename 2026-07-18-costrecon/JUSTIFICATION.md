# JUSTIFICATION — costrecon (2026-07-18)

## Problem
AWS estimated billing is frequently inaccurate versus actual cost — the HN #1 story
(1255pts, 2026-07-18) reports a $1.7B discrepancy in AWS's own estimated billing data, and
the broader FinOps pain is that teams budget against an estimate (Cost Explorer / budgets /
a spreadsheet) and only discover the gap weeks later when the real Cost & Usage Report (CUR)
lands. There is no lightweight, local, no-account way to diff "what I expected to spend"
against "what I actually spent" and to surface idle/over-provisioned resources that are
bleeding money every month.

## User
Any engineer, SRE, or FinOps practitioner with AWS spend who exports a CUR CSV and keeps a
simple estimates file. The operator themselves is a valid daily user (their own AWS bill).

## Why existing solutions are inadequate
Infracost estimates *pre-deploy* Terraform cost but does not reconcile *actual* vs *estimated*.
AWS Cost Anomaly Detection requires a console account and only does native anomaly alerts,
not estimated-vs-actual reconciliation from your own numbers. CloudZero/Vantage/etc. are
paid SaaS with onboarding friction. None of them are a zero-dependency CLI you can drop your
two CSVs into and get a quantified variance + savings report in seconds.

## Success criterion
`costrecon reconcile` flags any service whose actual spend diverges more than a configurable
tolerance (default 5%) from its estimate and lists unestimated spend; `costrecon idle`
quantifies monthly savings from idle compute, unattached EBS, unassociated EIPs, and stale
snapshots. Adopted if it produces a correct, useful variance + savings report on a real CUR
export. Build is verified by 40+ unit/CLI tests (including boundary and no-false-positive cases).
