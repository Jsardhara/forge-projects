"""FastAPI server — serves the health dashboard."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from healthpulse.aggregator import build_system_health
from healthpulse.models import HealthStatus

app = FastAPI(
    title="Jarmes Health Pulse",
    version="0.1.0",
    description="Lightweight log-based system health dashboard for Jarmes",
)

# Cached state
_last_health = None


def _status_color(status: HealthStatus) -> str:
    return {
        HealthStatus.HEALTHY: "#22c55e",
        HealthStatus.DEGRADED: "#f59e0b",
        HealthStatus.FAILING: "#ef4444",
        HealthStatus.UNKNOWN: "#6b7280",
    }.get(status, "#6b7280")


def _status_icon(status: HealthStatus) -> str:
    return {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.DEGRADED: "⚠️",
        HealthStatus.FAILING: "🔴",
        HealthStatus.UNKNOWN: "❓",
    }.get(status, "❓")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jarmes Health Pulse</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e4e4e7; min-height: 100vh; }
  .header { background: linear-gradient(135deg, #18181b 0%, #1e1e2e 100%); border-bottom: 1px solid #27272a; padding: 24px 32px; }
  .header h1 { font-size: 24px; font-weight: 600; color: #fafafa; }
  .header .subtitle { font-size: 14px; color: #a1a1aa; margin-top: 4px; }
  .header .generated { font-size: 12px; color: #71717a; margin-top: 8px; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px 32px; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .summary-card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; }
  .summary-card .label { font-size: 12px; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.05em; }
  .summary-card .value { font-size: 32px; font-weight: 700; margin-top: 8px; }
  .summary-card .sub { font-size: 13px; color: #71717a; margin-top: 4px; }
  .section { margin-bottom: 32px; }
  .section-title { font-size: 18px; font-weight: 600; color: #fafafa; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #27272a; }
  .job-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }
  .job-card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; transition: border-color 0.2s; }
  .job-card:hover { border-color: #3f3f46; }
  .job-card .job-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .job-card .job-name { font-size: 15px; font-weight: 600; color: #fafafa; font-family: 'JetBrains Mono', monospace; }
  .job-card .job-status { font-size: 13px; padding: 4px 10px; border-radius: 6px; font-weight: 500; }
  .job-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
  .job-metric { text-align: center; }
  .job-metric .num { font-size: 20px; font-weight: 700; }
  .job-metric .lbl { font-size: 11px; color: #71717a; text-transform: uppercase; }
  .job-bar { height: 4px; background: #27272a; border-radius: 2px; overflow: hidden; margin-bottom: 12px; }
  .job-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
  .job-error { font-size: 12px; color: #fca5a5; background: #1c1012; border: 1px solid #3d1515; border-radius: 6px; padding: 8px 12px; margin-top: 8px; word-break: break-all; }
  .job-suggestion { font-size: 12px; color: #86efac; background: #0c1a10; border: 1px solid #153d1f; border-radius: 6px; padding: 8px 12px; margin-top: 8px; }
  .pattern-list { list-style: none; }
  .pattern-item { background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 16px; margin-bottom: 8px; }
  .pattern-item .pattern-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .pattern-item .count { font-size: 18px; font-weight: 700; color: #ef4444; }
  .pattern-item .times { font-size: 11px; color: #71717a; }
  .pattern-item .sig { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #fca5a5; word-break: break-all; }
  .pattern-item .sample { font-size: 12px; color: #a1a1aa; margin-top: 4px; }
  .footer { text-align: center; padding: 32px; color: #52525b; font-size: 13px; }
  .refresh-btn { background: #27272a; border: 1px solid #3f3f46; color: #e4e4e7; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; margin-top: 12px; }
  .refresh-btn:hover { background: #3f3f46; }
</style>
</head>
<body>
<div class="header">
  <h1>⚡ Jarmes Health Pulse</h1>
  <div class="subtitle">Log-based system health dashboard</div>
  <div class="generated" id="generated">Loading...</div>
  <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
</div>
<div class="container">
  <div class="summary-grid" id="summary"></div>
  <div class="section">
    <div class="section-title">Cron Jobs</div>
    <div class="job-grid" id="jobs"></div>
  </div>
  <div class="section" id="patterns-section" style="display:none">
    <div class="section-title">Top Error Patterns</div>
    <ul class="pattern-list" id="patterns"></ul>
  </div>
</div>
<div class="footer">Jarmes Health Pulse v0.1.0 • Auto-refresh every 60s</div>
<script>
async function load() {
  const r = await fetch('/api/health?max_lines=5000');
  const d = await r.json();
  document.getElementById('generated').textContent = 'Generated: ' + new Date().toLocaleString();

  // Summary
  const statusColors = { healthy: '#22c55e', degraded: '#f59e0b', failing: '#ef4444', unknown: '#6b7280' };
  const statusIcons = { healthy: '✅', degraded: '⚠️', failing: '🔴', unknown: '❓' };
  const s = d.overall_status;
  document.getElementById('summary').innerHTML = `
    <div class="summary-card"><div class="label">Status</div><div class="value" style="color:${statusColors[s]}">${statusIcons[s]} ${s.toUpperCase()}</div></div>
    <div class="summary-card"><div class="label">Total Lines</div><div class="value">${d.total_lines_parsed.toLocaleString()}</div></div>
    <div class="summary-card"><div class="label">Errors</div><div class="value" style="color:#ef4444">${d.total_errors.toLocaleString()}</div></div>
    <div class="summary-card"><div class="label">Warnings</div><div class="value" style="color:#f59e0b">${d.total_warnings.toLocaleString()}</div></div>
    <div class="summary-card"><div class="label">Jobs</div><div class="value">${d.jobs.length}</div></div>
    <div class="summary-card"><div class="label">Log Sources</div><div class="value">${d.log_sources.length}</div><div class="sub">${d.log_sources.map(p=>p.split('\\\\').pop()).join(', ')}</div></div>
  `;

  // Jobs
  let jobsHtml = '';
  for (const j of d.jobs) {
    const sc = statusColors[j.status] || '#6b7280';
    const rate = (j.error_rate * 100).toFixed(1);
    const titleHtml = `<div class="job-header"><span class="job-name">${j.name}</span><span class="job-status" style="background:${sc}20;color:${sc}">${statusIcons[j.status]} ${j.status}</span></div>`;
    const metricsHtml = `<div class="job-metrics"><div class="job-metric"><div class="num">${j.total_runs}</div><div class="lbl">Runs</div></div><div class="job-metric"><div class="num" style="color:#ef4444">${j.total_errors}</div><div class="lbl">Errors</div></div><div class="job-metric"><div class="num" style="color:#22c55e">${j.total_successes}</div><div class="lbl">Success</div></div></div>`;
    const barHtml = `<div class="job-bar"><div class="job-bar-fill" style="width:${rate}%;background:${sc}"></div></div><div style="font-size:11px;color:#71717a;margin-bottom:8px">Error rate: ${rate}%</div>`;
    const errHtml = j.last_error ? `<div class="job-error">❌ ${j.last_error}</div>` : '';
    const sugHtml = j.suggestion ? `<div class="job-suggestion">💡 ${j.suggestion}</div>` : '';
    jobsHtml += `<div class="job-card">${titleHtml}${metricsHtml}${barHtml}${errHtml}${sugHtml}</div>`;
  }
  document.getElementById('jobs').innerHTML = jobsHtml || '<div style="color:#71717a;padding:32px;text-align:center">No job data found in logs</div>';

  // Patterns
  if (d.top_error_patterns && d.top_error_patterns.length > 0) {
    document.getElementById('patterns-section').style.display = '';
    let patHtml = '';
    for (const p of d.top_error_patterns.slice(0, 10)) {
      const suggestion = p.suggestion ? `<div class="job-suggestion" style="margin-top:8px">💡 ${p.suggestion}</div>` : '';
      patHtml += `<li class="pattern-item"><div class="pattern-header"><span class="count">×${p.count}</span><span class="times">${p.first_seen || ''} → ${p.last_seen || ''}</span></div><div class="sig">${p.pattern}</div><div class="sample">${p.sample_message || ''}</div>${suggestion}</li>`;
    }
    document.getElementById('patterns').innerHTML = patHtml;
  }
}
load();
setInterval(load, 60000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@app.get("/api/health")
async def api_health(
    max_lines: int = Query(default=5000, ge=100, le=50000),
    log_path: Optional[str] = Query(default=None),
):
    paths = [log_path] if log_path else None
    health = build_system_health(log_paths=paths, max_lines=max_lines)
    return JSONResponse(content=health.model_dump(mode="json"))


@app.get("/api/health/summary")
async def api_health_summary():
    health = build_system_health()
    return {
        "overall_status": health.overall_status.value,
        "total_errors": health.total_errors,
        "total_warnings": health.total_warnings,
        "jobs_count": len(health.jobs),
        "failing_jobs": [j.name for j in health.jobs if j.status == HealthStatus.FAILING],
        "generated_at": health.generated_at.isoformat(),
    }


def create_app() -> FastAPI:
    """Factory function for running with uvicorn."""
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8742)
