# Project Justification: restrictbot

## What Real Problem Does This Solve?
On 2026-07-29, the US government banned new foreign-made humanoids, robot dogs, and solar inverters citing national security risks. Physical AI hardware companies importing or manufacturing these products need a way to automatically check their product descriptions, parts lists, and BOMs against the restricted categories. Current solutions are manual customs review or manual legal review — no automated CLI tool exists.

## Who Is the User?
- Physical AI/hardware manufacturers importing components
- Robotics companies checking product compliance
- Customs brokers and trade compliance officers
- AI hardware startups needing pre-export compliance checks

## Why Existing Solutions Are Inadequate
- Manual customs review is slow and error-prone
- Legal compliance services are expensive ($500+/hr)
- No open-source CLI tool exists for this specific category
- Enterprise ERP systems don't cover this new regulation yet

## How We'll Know It's Successful
- `restrictbot check <product-desc>` returns PASS/WARN/FAIL with specific restricted categories triggered
- `restrictbot scan <bom.csv>` scans a complete parts list
- Exit code 1 on FAIL (CI gate mode)
- Covers at least 5 restricted categories (humanoids, robot dogs, solar inverters, and 2+ more)