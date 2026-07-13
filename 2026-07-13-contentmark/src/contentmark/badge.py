"""Reader-facing disclosure badge spec generator (contentmark)."""
from __future__ import annotations

from .models import Provenance, ProvenanceLabel

_LABEL_TEXT = {
    ProvenanceLabel.HUMAN: "Human-written",
    ProvenanceLabel.AI_ASSISTED: "AI-assisted",
    ProvenanceLabel.AI_GENERATED: "AI-generated",
    ProvenanceLabel.UNKNOWN: "Unverified",
}

_BAND_TEXT = {
    "human": "Reads as human-written",
    "possibly_ai": "Possibly AI-assisted",
    "likely_ai": "Likely AI-generated",
    "very_likely_ai": "Very likely AI-generated",
}


def badge_html(prov: Provenance, *, compact: bool = False) -> str:
    rid = prov.rid
    label = prov.label.value
    text = _LABEL_TEXT.get(prov.label, _LABEL_TEXT[ProvenanceLabel.UNKNOWN])
    meta_bits = []
    if prov.tool:
        meta_bits.append(f"tool: {prov.tool}")
    if prov.model:
        meta_bits.append(f"model: {prov.model}")
    if prov.author:
        meta_bits.append(f"author: {prov.author}")
    meta = " ".join(meta_bits)
    data = (
        f'data-cm-rid="{rid}" data-cm-label="{label}"'
        + (f' data-cm-meta="{meta}"' if meta else "")
    )
    if compact:
        inner = f'<span class="cm-badge__label">{text}</span>'
    else:
        inner = (
            f'<span class="cm-badge__label">{text}</span>'
            + (f'<span class="cm-badge__meta">{meta}</span>' if meta else "")
        )
    return (
        f'<span class="cm-badge cm-badge--{label}" {data} '
        f'role="note" aria-label="Content provenance: {text}">{inner}</span>'
    )


def badge_script() -> str:
    """Self-contained vanilla-JS widget: scans for cm-badge markup, no build step."""
    return (
        "/* contentmark badge widget — no dependencies, no build */\n"
        "(function(){\n"
        "  var BADGE_CLASS = 'cm-badge';\n"
        "  function audit(root){\n"
        "    var nodes = (root||document).querySelectorAll('.'+BADGE_CLASS);\n"
        "    var report = [];\n"
        "    nodes.forEach(function(n){\n"
        "      report.push({\n"
        "        rid: n.getAttribute('data-cm-rid'),\n"
        "        label: n.getAttribute('data-cm-label'),\n"
        "        meta: n.getAttribute('data-cm-meta') || ''\n"
        "      });\n"
        "    });\n"
        "    if (window.ContentMark) window.ContentMark.badges = report;\n"
        "    return report;\n"
        "  }\n"
        "  window.ContentMark = { audit: audit, version: '1.0' };\n"
        "  if (document.readyState !== 'loading') audit();\n"
        "  else document.addEventListener('DOMContentLoaded', function(){ audit(); });\n"
        "})();\n"
    )


def badge_css() -> str:
    return (
        ".cm-badge{display:inline-flex;flex-direction:column;gap:2px;"
        "font:500 12px/1.3 system-ui,sans-serif;padding:4px 10px;border-radius:999px;"
        "border:1px solid #cbd5e1;background:#f8fafc;color:#334155}\n"
        ".cm-badge__meta{font-weight:400;font-size:11px;color:#64748b}\n"
        ".cm-badge--ai_generated{background:#fef2f2;border-color:#fecaca;color:#991b1b}\n"
        ".cm-badge--ai_assisted{background:#fffbeb;border-color:#fde68a;color:#92400e}\n"
        ".cm-badge--human{background:#f0fdf4;border-color:#bbf7d0;color:#166534}\n"
        ".cm-badge--unknown{background:#f1f5f9;border-color:#e2e8f0;color:#475569}\n"
    )


def band_label(band_value: str) -> str:
    return _BAND_TEXT.get(band_value, band_value)
