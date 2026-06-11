# Project Justification

## Problem
npm v12 (July 2026) introduces breaking security defaults: `allowScripts` defaults to `off`, blocking all `preinstall`/`install`/`postinstall`/`prepare` scripts. Every company using npm must audit their dependency tree to identify which packages use install scripts, approve trusted ones, and configure their `package.json` for v12 compliance.

## User
Engineering teams and DevOps engineers managing Node.js/JavaScript projects. Specifically:
- Teams with CI/CD pipelines that will break on npm v12 upgrade
- Security teams enforcing supply chain compliance
- Developers preparing for the forced migration

## Why Existing Solutions Are Inadequate
- `npm audit` — scans for known vulnerabilities, does NOT map install scripts
- `better-npm-audit` — improved vulnerability output, still no v12 migration support
- `audit-ci` — CI integration for vulnerability thresholds, no install script analysis
- `npm-audit-resolver` — helps manage audit results, doesn't address allowScripts migration

No tool exists that specifically: scans the dependency tree for install scripts → generates the v12 allowlist configuration → provides risk scoring per package → outputs CI/CD-ready reports.

## Success Criteria
- CLI that scans any `package-lock.json` and reports install scripts
- Generates v12-compliant allowlist JSON
- Risk scoring based on script count, package popularity, and known supply chain attacks
- Test coverage > 90%
- Published to forge-projects repo
