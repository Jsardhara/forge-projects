# Project Justification: apk-signal

## Problem
A new Android malware strain (disclosed by F-Droid, HN #1 on 2026-07-01 at 490 points)
shows malicious apps are still reaching users through sideloading and third-party stores.
SOC analysts, threat researchers, and security-conscious users need a fast first-pass triage
tool that pulls actionable signals out of an APK *without* standing up apktool, Androguard, or
a full reverse-engineering workbench. Existing open-source tooling (Androguard, MobSF) is heavy,
requires Python deps / a server, and is overkill for a 30-second "should I even look closer?"
signal sweep.

## User
- Threat researchers doing bulk intake triage on a folder of suspect APKs.
- Security engineers validating their own builds for accidentally-bundled secrets/C2 strings.
- Curious users scanning an APK they were sent before installing it.

## Why existing solutions are inadequate
- **Androguard / MobSF**: powerful but heavy; require dependency installs, a running server
  (MobSF), or deep library knowledge. Not a `pip install && apk-signal file.apk` one-shot.
- **VirusTotal**: needs upload + network + API key, gives a verdict but not a structured,
  offline, scriptable signal extraction you can pipe into your own pipeline.
- No stdlib-only, zero-dependency, CI-friendly CLI exists for *signal extraction* specifically.

## What this builds
`apk-signal` is a pure-stdlib static analyzer. It treats the APK as a ZIP, walks every entry,
and scans raw bytes (decoded losslessly as latin-1) for:
- Network indicators: URLs, bare domains, IPv4 addresses
- Hardcoded secrets: AWS/Google/Slack/Stripe/Telegram keys, PEM private keys, JWTs
- Declared permissions (extracted from the compiled manifest string pool)
- Suspicious capability keywords (accessibility abuse, overlays, SMS intercept, credential
  theft, OTP/2FA stealing, lock-screen/crypto-wallet bait) with negation filtering
- Native library (.so) inventory and multi-dex detection
It aggregates into a weighted risk score (CRITICAL/HIGH/MEDIUM/LOW) with a machine-readable
JSON mode for pipelines.

## Success criteria
- `pip install .` works with zero external dependencies.
- `apk-signal sample.apk` prints a ranked signal report; `--json` emits structured data.
- A self-built synthetic APK (zip of crafted entries) is correctly scored by the test suite.
- Each detector has unit tests, including negation false-positive guards.

## Distinction from prior builds (dedup)
- Not `zero-day-sentinel` (repo/dependency CVE scanning) — different domain (mobile binaries).
- Not `mcp-shield` / `ai-leak-scanner` (agent/runtime security) — different artifact class.
- Category "mobile malware / APK signal extraction" is novel in the forge-projects index.
