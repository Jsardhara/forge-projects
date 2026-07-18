# costrecon — Local AWS Billing Reconciliation

Zero-dependency CLI that reconciles your **estimated** AWS spend against **actual** Cost &
Usage Report (CUR) spend, and detects **idle / over-provisioned** resources bleeding money.

Built in response to the HN #1 FinOps story (2026-07-18): *"AWS: Inaccurate Estimated
Billing Data – $1.7 billion."* You already have the two inputs — a CUR CSV export and a
simple estimates file. `costrecon` tells you where reality diverged from plan and where you
can cut cost, with real dollar figures.

## Install

```bash
pip install .
# or, for development:
python -m pip install -e ".[dev]"
```

Requires Python 3.9+. **No third-party dependencies.**

## Inputs

**1. CUR CSV** — the AWS Cost & Usage Report (or any CSV with a recognizable cost column).
`costrecon` understands the full CUR column naming (`lineItem/UnblendedCost`,
`product/ProductName`, …) and a simplified `service,cost,…` schema.

**2. Estimates CSV** — your budget / expected spend per service:

```csv
key,estimated_cost,note
Amazon Elastic Compute Cloud,10500.00,
Amazon Simple Storage Service,2250.00,
```

**3. Utilization CSV** (for `idle` / `audit`) — one row per billable resource:

```csv
resource_id,type,utilization_pct,monthly_cost,region,state,age_days
i-0a1b,ec2,3.2,420.00,us-east-1,,
vol-0x,ebs,,,18.50,us-east-1,unattached,
eip-0y,eip,,,4.00,us-east-1,available,
snap-0z,snapshot,,,2.10,us-east-1,,95
```

`type` is one of `ec2|ebs|eip|snapshot|rds|other`. `utilization_pct`, `state`, and `age_days`
are optional and used where relevant.

## Commands

### reconcile — estimated vs actual

```bash
costrecon reconcile --cur cur.csv --estimates est.csv --format text
costrecon reconcile --cur cur.csv --estimates est.csv --threshold 5 --strict --format json
```

Flags services whose actual spend diverges more than `--threshold` % (default 5) from the
estimate, and lists services present in the CUR with **no estimate** (unexpected spend).
With `--strict`, exits `1` if any anomaly is found (useful as a CI / cron gate).

### idle — idle / over-provisioned resources

```bash
costrecon idle --utilization util.csv --idle-threshold 5 --snapshot-max-age 30 --format text
```

Flags compute resources below the utilization threshold, unattached EBS volumes, unassociated
Elastic IPs, and snapshots older than the age threshold — each with an **estimated monthly
savings** figure.

### audit — run both at once

```bash
costrecon audit --cur cur.csv --estimates est.csv --utilization util.csv --format json
```

## Example output (text)

```
COST RECONCILIATION
  Total estimated : $12,750.00
  Total actual    : $12,750.00
  Delta           : $0.00 (0.0%)

IDLE / OVER-PROVISIONED RESOURCES
  Monthly cost reviewed : $225.00
  Potential savings     : $125.33 (4 findings)

CRITICAL (1):
  i-idle (ec2) $100.00/mo -> save $99.00 : utilization 1.0% < 5.0% threshold
WARN (1):
  snap-1 (snapshot) $2.00/mo -> save $1.33 : snapshot age 90d > 30d
...
```

## Programmatic use

```python
from costrecon import parse_cur, summarize_by_service, Reconciler, IdleDetector

items = parse_cur("cur.csv")
actuals = summarize_by_service(items)
report = Reconciler(threshold_pct=5.0).reconcile(actuals, estimates)
```

## Tests

```bash
pytest tests/ -v
```

## License

MIT
