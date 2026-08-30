# Project Justification — songguard

**What real problem does this solve?** On 2026-08-29 Sony Music and Warner sued Anthropic
alleging a "brazen campaign" of intellectual-property theft in AI music generation (TechCrunch;
Lens Op #1). A label or gen-AI music startup must screen an LLM-produced lyric against its
licensed catalog *before release* to catch verbatim or near-verbatim sampling / infringement.
Today that check is either manual (a human Googling phrases) or absent. The portfolio has AI-text
detection (contentmark) and license parsing (licguard), but **nothing screens candidate content
against a reference corpus for copyright risk** at the similarity layer.

**Who is the user?** A label compliance analyst, a gen-AI music platform's release gate, or a
producer running `songguard screen my_line.ai.txt catalog/` before shipping — deterministic,
offline, auditable.

**Why are existing solutions inadequate?** Paid B2B plagiarism/clearance suites are heavyweight
SaaS (the "3-4 wk MVP with a label" Lens scoped); `contentmark` detects whether *text is AI
generated*, not whether *lyrics infringe a catalog*. Nothing standalone, zero-dependency, and
local gives a pre-deployment infringement gate. This is Lens Op #1's named "copyright screening
middleware" step, built as a self-contained CLI.

**How will we know it's successful?** Verbatim/reused lyric segments produce INFRINGE with a
documented "sampled phrase" and CI exit 1; genuinely original lyrics against an unrelated catalog
return CLEAR with zero false positives; common-phrase coincidences (short runs) do not flag.
Success = deterministic verdicts across those three fixture classes, all green.