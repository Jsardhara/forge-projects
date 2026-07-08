# apk-signal

A **zero-dependency static triage signal extractor for Android APK files**. Point it at a
suspect APK and get a ranked list of risk signals in seconds — no apktool, no Androguard, no
server.

Built in response to the [new Android malware disclosure](https://f-droid.org/2026/07/01/adv-malware.html)
(Hacker News #1, 2026-07-01). Useful for SOC intake triage, security engineers validating
their own builds for accidentally-bundled secrets/C2 strings, and cautious users scanning an
APK before installing it.

## How it works

An APK is just a ZIP. `apk-signal` walks every entry, decodes the bytes losslessly as
`latin-1`, and scans the text for:

| Signal | What it catches |
|--------|-----------------|
| **Network indicators** | `http(s)://` URLs, bare domains, IPv4 addresses (C2 beacons) |
| **Hardcoded secrets** | AWS keys, Google API keys, Slack tokens, Stripe live keys, Telegram bot tokens, PEM private keys, JWTs, generic `key=`/`secret=` assignments |
| **Permissions** | Declared `android.permission.*` + custom perms, weighted by danger (accessibility binding, SMS read, device admin = high) |
| **Suspicious capabilities** | Accessibility abuse, overlays, SMS interception, credential theft, OTP/2FA theft, crypto-wallet targeting, ransomware/lock-screen, root hide |
| **Structure** | Native `.so` libraries present, multi-dex packaging |

Each signal carries a severity (CRITICAL/HIGH/MEDIUM/LOW/INFO) and a weighted score. The
aggregate `risk_score` is capped at 100 and mapped to a risk level. Negation filtering
avoids false positives on benign mentions like *"this app does not steal credentials"*.

## Install

```bash
pip install .
```

No external dependencies. Requires Python 3.9+.

## Usage

```bash
# Human-readable report
apk-signal path/to/suspect.apk

# Machine-readable JSON (pipe into your pipeline)
apk-signal path/to/suspect.apk --json

# Only show HIGH and above
apk-signal path/to/suspect.apk --min-severity HIGH
```

### Sample output

```
================================================================
APK SIGNAL REPORT: evil.apk
================================================================
Package      : com.evil.spyware
Entries      : 5  |  DEX: 2  |  Native libs: 1
Permissions  : 7 declared
Risk score   : 84/100  (CRITICAL)

SIGNALS (12)
----------------------------------------------------------------
[CRITICAL] AWS Access Key ID
           AKIAIO...MPLE
           @ classes.dex
[CRITICAL] Credential / password theft
           steal passwords from the victim
           @ classes.dex
...
```

## Library use

```python
from apk_signal import analyze

result = analyze("suspect.apk")
print(result.risk_level, result.risk_score)
for s in result.signals:
    print(s.severity, s.label, s.detail)
```

## Limitations

This is a **first-pass static signal scan**, not a substitute for full dynamic analysis or a
decompiler. It does not:

- Decompile DEX/SMALI (it scans the raw string pool, so obfuscated strings are invisible).
- Validate certificate / signing info.
- Detect packed or encrypted payloads.

For deeper analysis, feed high-scoring APKs to MobSF or Androguard.

## License

MIT
