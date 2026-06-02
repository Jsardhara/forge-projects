"""FastAPI dashboard for AI Cost Guard."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from aicostguard.pricing import ALL_PRICES
from aicostguard.tracker import Budget, UsageRecord, UsageTracker


# ── HTML Dashboard ──────────────────────────────────────────────────────────

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Cost Guard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; padding: 2rem; }
h1 { font-size: 1.8rem; margin-bottom: 1.5rem; color: #7dd3fc; }
h2 { font-size: 1.2rem; margin: 1.5rem 0 0.75rem; color: #94a3b8; }
.card { background: #1e2130; border: 1px solid #2d3748; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
.stat { text-align: center; }
.stat .value { font-size: 2rem; font-weight: 700; color: #7dd3fc; }
.stat .label { font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }
table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
th, td { text-align: left; padding: 0.6rem 0.75rem; border-bottom: 1px solid #2d3748; font-size: 0.9rem; }
th { color: #64748b; font-weight: 500; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-alert { background: #7f1d1d; color: #fca5a5; }
.badge-warning { background: #713f12; color: #fde68a; }
.badge-ok { background: #14532d; color: #86efac; }
.alert-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; background: #1e2130; border-radius: 8px; margin-bottom: 0.5rem; border: 1px solid #2d3748; }
.savings { color: #86efac; font-weight: 600; }
</style>
</head>
<body>
<h1>🛡️ AI Cost Guard</h1>

<div class="grid">
  <div class="card stat">
    <div class="value" id="daily-spend">$0.00</div>
    <div class="label">Daily Spend</div>
  </div>
  <div class="card stat">
    <div class="value" id="weekly-spend">$0.00</div>
    <div class="label">Weekly Spend</div>
  </div>
  <div class="card stat">
    <div class="value" id="monthly-spend">$0.00</div>
    <div class="label">Monthly Spend</div>
  </div>
  <div class="card stat">
    <div class="value" id="alerts-count">0</div>
    <div class="label">Active Alerts</div>
  </div>
</div>

<h2>📊 Spend by Model</h2>
<div class="card">
  <table>
    <thead><tr><th>Provider</th><th>Model</th><th>Cost</th><th>Input Tokens</th><th>Output Tokens</th><th>Calls</th></tr></thead>
    <tbody id="spend-table"><tr><td colspan="6" style="color:#64748b">No data yet</td></tr></tbody>
  </table>
</div>

<h2>⚠️ Alerts</h2>
<div class="card" id="alerts-section"><p style="color:#64748b">No alerts</p></div>

<h2>💡 Waste Report</h2>
<div class="card" id="waste-section"><p style="color:#64748b">No waste detected</p></div>

<script>
async function loadDashboard() {
  // Spend summary
  for (const period of ['daily','weekly','monthly']) {
    const r = await fetch(`/api/spend?period=${period}`);
    const d = await r.json();
    document.getElementById(period + '-spend').textContent = '$' + d.total.toFixed(4);
  }

  // Spend by model
  const sr = await fetch('/api/spend/by-model?period=daily');
  const sd = await sr.json();
  const tbody = document.getElementById('spend-table');
  if (sd.length > 0) {
    tbody.innerHTML = sd.map(r => `<tr>
      <td>${r.provider}</td><td>${r.model}</td><td>$${r.total_cost.toFixed(4)}</td>
      <td>${r.total_input.toLocaleString()}</td><td>${r.total_output.toLocaleString()}</td><td>${r.call_count}</td>
    </tr>`).join('');
  }

  // Alerts
  const ar = await fetch('/api/alerts');
  const ad = await ar.json();
  document.getElementById('alerts-count').textContent = ad.length;
  const as = document.getElementById('alerts-section');
  if (ad.length > 0) {
    as.innerHTML = ad.map(a => `
      <div class="alert-item">
        <span class="badge badge-${a.severity === 'alert' ? 'alert' : 'warning'}">${a.severity}</span>
        <span>${a.message}</span>
      </div>`).join('');
  }

  // Waste
  const wr = await fetch('/api/waste?period=daily');
  const wd = await wr.json();
  const ws = document.getElementById('waste-section');
  if (wd.length > 0) {
    ws.innerHTML = `<p style="margin-bottom:0.75rem" class="savings">Total potential savings: $${wd.reduce((s,x)=>s+x.estimated_savings,0).toFixed(4)}</p>`
      + wd.map(w => `<div class="alert-item">
        <div><strong>${w.current_provider}/${w.current_model}</strong> → <strong>${w.suggested_provider}/${w.suggested_model}</strong><br>
        <span style="color:#64748b">Currently $${w.current_cost.toFixed(4)} (${w.call_count} calls). Save ~<span class="savings">$${w.estimated_savings.toFixed(4)} (${w.savings_pct}%)</span></span></div>
      </div>`).join('');
  }
}
loadDashboard();
setInterval(loadDashboard, 30000);
</script>
</body>
</html>
"""


# ── App ─────────────────────────────────────────────────────────────────────

# Module-level tracker; tests override via app.state
tracker = UsageTracker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="AI Cost Guard",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@app.get("/api/spend")
async def get_spend(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    provider: str = "all",
    team: str = "default",
):
    total = tracker.get_total_spend(team_id=team, provider=provider, period=period)
    return {"total": total, "period": period, "provider": provider, "team": team}


@app.get("/api/spend/by-model")
async def get_spend_by_model(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    team: str = "default",
):
    return tracker.get_spend_by_model(team_id=team, period=period)


@app.post("/api/track")
async def track_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    team: str = "default",
    tags: str = "",
):
    record = UsageRecord(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        team_id=team,
        tags=tags,
    )
    row_id = tracker.record_usage(record)
    return {"id": row_id, "estimated_cost": record.estimated_cost}


@app.get("/api/alerts")
async def get_alerts(team: str = "default"):
    return tracker.get_alerts(team_id=team, unacknowledged_only=True)


@app.post("/api/budget")
async def set_budget(
    limit_usd: float,
    provider: str = "all",
    model: str = "all",
    period: str = "daily",
    alert_at_pct: float = 80.0,
    team: str = "default",
):
    budget = Budget(
        team_id=team,
        provider=provider,
        model=model,
        period=period,
        limit_usd=limit_usd,
        alert_at_pct=alert_at_pct,
    )
    row_id = tracker.set_budget(budget)
    return {"id": row_id, "limit_usd": limit_usd, "period": period}


@app.post("/api/budget/check")
async def check_budgets(team: str = "default"):
    alerts = tracker.check_budgets(team_id=team)
    return {"alerts": [{"severity": a.severity, "message": a.message, "type": a.alert_type} for a in alerts]}


@app.get("/api/waste")
async def get_waste(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    team: str = "default",
):
    return tracker.get_waste_report(team_id=team, period=period)


@app.get("/api/prices")
async def get_prices():
    return ALL_PRICES
