"""FastAPI application for RegShield."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from regshield.models import Jurisdiction, RiskLevel, UseCase
from regshield.store import store
from regshield.templates import render_dashboard

app = FastAPI(
    title="RegShield",
    description="AI Compliance & Regulatory Shield Platform",
    version="0.1.0",
)


# -- API Endpoints --

@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "regshield", "version": "0.1.0"}


@app.get("/api/models")
async def list_models() -> list[dict]:
    """List all tracked AI models."""
    return [m.model_dump() for m in store.list_models()]


@app.get("/api/models/{model_id:path}")
async def get_model(model_id: str) -> dict:
    """Get a specific model by ID."""
    model = store.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model.model_dump()


@app.get("/api/statuses")
async def list_statuses(
    jurisdiction: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
) -> list[dict]:
    """List regulatory statuses, optionally filtered."""
    j = Jurisdiction(jurisdiction) if jurisdiction else None
    r = RiskLevel(risk_level) if risk_level else None
    return [s.model_dump() for s in store.list_statuses(jurisdiction=j, risk_level=r)]


@app.get("/api/check")
async def check_compliance(
    model_id: str = Query(...),
    jurisdiction: str = Query(...),
    use_case: str = Query("general"),
) -> dict:
    """Check compliance for a model in a jurisdiction."""
    try:
        j = Jurisdiction(jurisdiction)
        uc = UseCase(use_case)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = store.check_compliance(model_id, j, uc)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_id}' not found in registry. Add it first.",
        )
    return result.model_dump()


@app.get("/api/alerts")
async def list_alerts(
    unread_only: bool = Query(False),
) -> list[dict]:
    """List regulatory change alerts."""
    return [a.model_dump() for a in store.list_alerts(unread_only=unread_only)]


@app.get("/api/audit-log")
async def audit_log(
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    """List audit log entries."""
    return [e.model_dump() for e in store.list_audit_log(limit=limit)]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> dict:
    """Acknowledge an alert."""
    if store.acknowledge_alert(alert_id):
        return {"acknowledged": True, "alert_id": alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")


# -- Dashboard --

@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    """Serve the compliance dashboard."""
    models = store.list_models()
    alerts = store.list_alerts(unread_only=True)
    restricted = store.list_statuses(risk_level=RiskLevel.BANNED)
    pending = store.list_statuses(risk_level=RiskLevel.PENDING_REVIEW)
    return render_dashboard(models, alerts, restricted, pending)
