"""HTML template rendering for the RegShield dashboard.

Uses Jinja2 with a self-contained template (no external files needed).
Clean, professional design — no AI slop.
"""

from __future__ import annotations

from regshield.models import AIModel, Alert, RegulatoryStatus, RiskLevel


def _risk_badge(risk_level: RiskLevel | str) -> str:
    """Render a colored badge for a risk level."""
    if isinstance(risk_level, str):
        risk_level = RiskLevel(risk_level)

    colors = {
        RiskLevel.COMPLIANT: ("#065f46", "#d1fae5", "✓"),
        RiskLevel.PENDING_REVIEW: ("#92400e", "#fef3c7", "◐"),
        RiskLevel.RESTRICTED: ("#9a3412", "#fed7aa", "⚠"),
        RiskLevel.BANNED: ("#991b1b", "#fecaca", "✕"),
        RiskLevel.UNKNOWN: ("#374151", "#e5e7eb", "?"),
    }
    fg, bg, icon = colors.get(risk_level, colors[RiskLevel.UNKNOWN])
    label = risk_level.value.replace("_", " ").upper()
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:9999px;'
        f"background:{bg};color:{fg};font-size:12px;font-weight:600;"
        f'font-family:Inter,sans-serif">{icon} {label}</span>'
    )


def render_dashboard(
    models: list[AIModel],
    alerts: list[Alert],
    restricted: list[RegulatoryStatus],
    pending: list[RegulatoryStatus],
) -> str:
    """Render the full dashboard HTML page."""
    escaped = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    # Alert banner
    alert_html = ""
    if alerts:
        alert_items = "".join(
            f'<div style="padding:12px 16px;background:#fef3c7;border-left:4px solid #f59e0b;'
            f"border-radius:4px;margin-bottom:8px;font-size:14px;"
            f'font-family:Inter,sans-serif">'
            f'<strong style="color:#92400e">{escaped(a.model_name)} ({escaped(a.jurisdiction.value)}):</strong> '
            f'{escaped(a.description)} '
            f'<span style="color:#78716c;font-size:12px">— {escaped(a.previous_status.value)} → '
            f'{escaped(a.new_status.value)}</span>'
            f'<span style="color:#a8a29e;font-size:11px;float:right">{escaped(a.alert_id)}</span>'
            f"</div>"
            for a in alerts[:5]
        )
        alert_html = f"""
        <section style="margin-bottom:32px">
            <h2 style="font-size:18px;font-weight:700;margin-bottom:12px;color:#dc2626;
                       font-family:Inter,sans-serif">🚨 Active Alerts ({len(alerts)})</h2>
            {alert_items}
        </section>"""

    # Stats row
    total_models = len(models)
    banned_count = len(restricted)
    pending_count = len(pending)

    stats_html = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:32px">
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px">
            <div style="font-size:13px;color:#6b7280;font-family:Inter,sans-serif">Models Tracked</div>
            <div style="font-size:32px;font-weight:700;color:#111827;font-family:Inter,sans-serif">{total_models}</div>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px">
            <div style="font-size:13px;color:#6b7280;font-family:Inter,sans-serif">Banned / Restricted</div>
            <div style="font-size:32px;font-weight:700;color:#dc2626;font-family:Inter,sans-serif">{banned_count}</div>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px">
            <div style="font-size:13px;color:#6b7280;font-family:Inter,sans-serif">Pending Review</div>
            <div style="font-size:32px;font-weight:700;color:#d97706;font-family:Inter,sans-serif">{pending_count}</div>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px">
            <div style="font-size:13px;color:#6b7280;font-family:Inter,sans-serif">Active Alerts</div>
            <div style="font-size:32px;font-weight:700;color:#7c3aed;font-family:Inter,sans-serif">{len(alerts)}</div>
        </div>
    </div>"""

    # Model registry table
    table_rows = "".join(
        f"""<tr>
            <td style="padding:10px 12px;font-weight:600;font-size:14px">
                <a href="/api/models/{escaped(m.model_id)}" style="color:#1d4ed8;text-decoration:none"
                   onmouseover="this.style.textDecoration='underline'"
                   onmouseout="this.style.textDecoration='none'">{escaped(m.name)}</a>
            </td>
            <td style="padding:10px 12px;font-size:13px;color:#6b7280">{escaped(m.provider.value)}</td>
            <td style="padding:10px 12px;font-size:13px;color:#6b7280">{escaped(m.version)}</td>
            <td style="padding:10px 12px;font-size:12px;color:#6b7280">
                <code style="background:#f3f4f6;padding:2px 6px;border-radius:4px">{escaped(m.model_id)}</code>
            </td>
            <td style="padding:10px 12px;font-size:13px;color:#374151;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{escaped(m.notes) if m.notes else "—"}</td>
        </tr>"""
        for m in models
    )

    table_html = f"""
    <section style="margin-bottom:32px">
        <h2 style="font-size:18px;font-weight:700;margin-bottom:12px;font-family:Inter,sans-serif">Model Registry</h2>
        <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:8px">
            <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif">
                <thead>
                    <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;text-align:left">
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Model</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Provider</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Version</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">ID</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </section>"""

    # Compliance checker section
    checker_html = """
    <section style="margin-bottom:32px">
        <h2 style="font-size:18px;font-weight:700;margin-bottom:12px;font-family:Inter,sans-serif">Compliance Checker</h2>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px">
            <form id="checkForm" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
                <div>
                    <label style="display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:4px;font-family:Inter,sans-serif">Model ID</label>
                    <input id="modelId" type="text" placeholder="e.g. anthropic/claude-sonnet-4"
                           style="padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;width:280px;font-family:Inter,sans-serif">
                </div>
                <div>
                    <label style="display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:4px;font-family:Inter,sans-serif">Jurisdiction</label>
                    <select id="jurisdiction" style="padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;font-family:Inter,sans-serif">
                        <option value="US">United States (US)</option>
                        <option value="EU">European Union (EU)</option>
                        <option value="UK">United Kingdom (UK)</option>
                        <option value="CN">China (CN)</option>
                        <option value="IN">India (IN)</option>
                        <option value="CA">Canada (CA)</option>
                        <option value="AU">Australia (AU)</option>
                        <option value="JP">Japan (JP)</option>
                        <option value="KR">South Korea (KR)</option>
                        <option value="BR">Brazil (BR)</option>
                    </select>
                </div>
                <div>
                    <label style="display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:4px;font-family:Inter,sans-serif">Use Case</label>
                    <select id="useCase" style="padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;font-family:Inter,sans-serif">
                        <option value="general">General</option>
                        <option value="government">Government</option>
                        <option value="defense">Defense</option>
                        <option value="healthcare">Healthcare</option>
                        <option value="financial">Financial</option>
                        <option value="education">Education</option>
                        <option value="research">Research</option>
                        <option value="export">Export</option>
                    </select>
                </div>
                <button type="submit"
                        style="padding:8px 20px;background:#111827;color:#fff;border:none;border-radius:6px;
                               font-size:14px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif;
                               transition:background 0.15s"
                        onmouseover="this.style.background='#374151'"
                        onmouseout="this.style.background='#111827'">
                    Check Compliance
                </button>
            </form>
            <div id="result" style="margin-top:16px"></div>
        </div>
    </section>"""

    # Restricted/Pending table
    restricted_rows = "".join(
        f"""<tr>
            <td style="padding:10px 12px;font-weight:600;font-size:14px">{escaped(s.model_id)}</td>
            <td style="padding:10px 12px;font-size:13px">{escaped(s.jurisdiction.value)}</td>
            <td style="padding:10px 12px">{_risk_badge(s.risk_level)}</td>
            <td style="padding:10px 12px;font-size:13px;color:#374151">{" • ".join(escaped(r) for r in s.restrictions[:3])}</td>
            <td style="padding:10px 12px;font-size:12px;color:#6b7280">{escaped(s.notes) if s.notes else "—"}</td>
        </tr>"""
        for s in restricted + pending
    )

    restricted_html = ""
    if restricted or pending:
        restricted_html = f"""
    <section style="margin-bottom:32px">
        <h2 style="font-size:18px;font-weight:700;margin-bottom:12px;font-family:Inter,sans-serif">Restricted & Pending Models</h2>
        <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:8px">
            <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif">
                <thead>
                    <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;text-align:left">
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Model</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Jurisdiction</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Status</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Restrictions</th>
                        <th style="padding:12px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em">Notes</th>
                    </tr>
                </thead>
                <tbody>{restricted_rows}</tbody>
            </table>
        </div>
    </section>"""

    # Footer
    footer_html = """
    <footer style="margin-top:48px;padding-top:24px;border-top:1px solid #e5e7eb;text-align:center">
        <p style="font-size:12px;color:#9ca3af;font-family:Inter,sans-serif">
            RegShield v0.1.0 — AI Compliance & Regulatory Shield Platform &middot;
            Built by Forge (Jarmes) &middot;
            Data seeded from real regulatory events (June 2026)
        </p>
    </footer>"""

    # Full page
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegShield — AI Compliance Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #f9fafb; color: #111827; font-family: Inter, sans-serif; }}
        tr:hover {{ background: #f9fafb; }}
        tr {{ border-bottom: 1px solid #f3f4f4; }}
        tr:last-child {{ border-bottom: none; }}
    </style>
</head>
<body style="max-width:1200px;margin:0 auto;padding:32px 24px">

    <header style="margin-bottom:32px">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
            <div style="width:36px;height:36px;background:#111827;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;
                        color:#fff;font-weight:700;font-size:18px">R</div>
            <h1 style="font-size:24px;font-weight:700;font-family:Inter,sans-serif">RegShield</h1>
        </div>
        <p style="font-size:14px;color:#6b7280;margin-left:48px">
            AI Compliance & Regulatory Shield Platform — Track model restrictions by jurisdiction in real-time
        </p>
    </header>

    {alert_html}
    {stats_html}
    {checker_html}
    {restricted_html}
    {table_html}
    {footer_html}

    <script>
    document.getElementById('checkForm').addEventListener('submit', async function(e) {{
        e.preventDefault();
        const modelId = document.getElementById('modelId').value.trim();
        const jurisdiction = document.getElementById('jurisdiction').value;
        const useCase = document.getElementById('useCase').value;
        const resultDiv = document.getElementById('result');

        if (!modelId) {{
            resultDiv.innerHTML = '<div style="padding:12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;color:#991b1b;font-size:14px">Please enter a model ID</div>';
            return;
        }}

        resultDiv.innerHTML = '<div style="padding:12px;color:#6b7280;font-size:14px">Checking...</div>';

        try {{
            const resp = await fetch(`/api/check?modelId=${{encodeURIComponent(modelId)}}&jurisdiction=${{jurisdiction}}&useCase=${{useCase}}`);
            const data = await resp.json();

            if (resp.status === 404) {{
                resultDiv.innerHTML = `<div style="padding:12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;color:#991b1b;font-size:14px"><strong>Not Found:</strong> ${{data.detail}} <br><span style="font-size:12px;color:#6b7280">Browse the model registry below to find the correct model ID.</span></div>`;
                return;
            }}

            const allowed = data.is_allowed;
            const badgeColor = allowed ? '#d1fae5' : '#fecaca';
            const badgeFg = allowed ? '#065f46' : '#991b1b';
            const badgeText = allowed ? '✓ ALLOWED' : '✕ RESTRICTED';
            const riskColor = data.risk_level === 'banned' ? '#991b1b' : data.risk_level === 'compliant' ? '#065f46' : '#92400e';

            let restrictionsHtml = '';
            if (data.restrictions && data.restrictions.length > 0) {{
                restrictionsHtml = '<ul style="margin:8px 0 0 20px;font-size:13px;color:#374151">' +
                    data.restrictions.map(r => `<li>${{r}}</li>`).join('') + '</ul>';
            }}

            resultDiv.innerHTML = `
                <div style="padding:16px;background:${{allowed ? '#f0fdf4' : '#fef2f2'}};border:1px solid ${{allowed ? '#bbf7d0' : '#fecaca'}};border-radius:8px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                        <strong style="font-size:16px">${{data.model_name}}</strong>
                        <span style="padding:4px 12px;border-radius:9999px;background:${{badgeColor}};color:${{badgeFg}};font-size:13px;font-weight:600">${{badgeText}}</span>
                    </div>
                    <div style="font-size:13px;color:#6b7280">
                        <strong>Jurisdiction:</strong> ${{data.jurisdiction}} &middot;
                        <strong>Use Case:</strong> ${{data.use_case}} &middot;
                        <strong>Risk:</strong> <span style="color:${{riskColor}};font-weight:600">${{data.risk_level.toUpperCase()}}</span>
                    </div>
                    ${{restrictionsHtml}}
                    ${{data.notes ? `<div style="margin-top:8px;font-size:13px;color:#374151"><strong>Notes:</strong> ${{data.notes}}</div>` : ''}}
                    ${{data.source_url ? `<div style="margin-top:4px;font-size:12px"><a href="${{data.source_url}}" target="_blank" style="color:#1d4ed8">Source →</a></div>` : ''}}
                </div>
            `;
        }} catch (err) {{
            resultDiv.innerHTML = `<div style="padding:12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;color:#991b1b;font-size:14px">Error: ${{err.message}}</div>`;
        }}
    }});
    </script>
</body>
</html>"""
