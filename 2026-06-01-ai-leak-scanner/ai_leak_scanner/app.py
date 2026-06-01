"""FastAPI REST API for AI Leak Scanner.

Endpoints:
    GET  /health          — Health check
    GET  /vulns           — List all vulnerabilities
    GET  /vulns/{vid}     — Get vulnerability by ID
    GET  /vulns/vendor/{vendor} — Get vulnerabilities by vendor
    GET  /vulns/severity/{level} — Get vulnerabilities by severity
    POST /scan            — Scan installed extensions
    POST /audit           — Full database audit
    GET  /stats           — Database statistics
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .vulndb import (
    VULNERABILITIES,
    Severity,
    get_vulnerability,
    get_by_vendor,
    get_by_severity,
    get_unpatched,
    get_attack_vectors,
)
from .scanner import scan_extensions, scan_all, get_risk_level

app = FastAPI(
    title="AI Leak Scanner",
    version="0.1.0",
    description="Security audit API for AI extensions and agents",
)


# ── Pydantic models ─────────────────────────────────────────────────────────

class ExtensionItem(BaseModel):
    name: str
    vendor: Optional[str] = None


class ScanRequest(BaseModel):
    extensions: list[str]
    target: str = "api"


class FindingOut(BaseModel):
    id: str
    name: str
    vendor: str
    product: str
    severity: str
    detected: bool
    confidence: float
    patched: bool
    description: str
    mitigation: str


class ScanResponse(BaseModel):
    scan_id: str
    timestamp: str
    target: str
    risk_score: float
    risk_level: str
    summary: str
    findings: list[FindingOut]


class StatsResponse(BaseModel):
    total_vulnerabilities: int
    unpatched: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    vendors: list[str]
    attack_vectors: list[str]


class VulnSummary(BaseModel):
    id: str
    name: str
    vendor: str
    product: str
    severity: str
    patched: bool


class VulnDetail(VulnSummary):
    attack_vectors: list[str]
    description: str
    impact: str
    mitigation: str
    cve: str
    disclosed: str
    patch_note: str
    references: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    vulndb_count: int


# ── Helpers ──────────────────────────────────────────────────────────────────

def _vuln_to_summary(v) -> VulnSummary:
    return VulnSummary(
        id=v.vid,
        name=v.name,
        vendor=v.vendor,
        product=v.product,
        severity=v.severity.value,
        patched=v.patched,
    )


def _vuln_to_detail(v) -> VulnDetail:
    return VulnDetail(
        id=v.vid,
        name=v.name,
        vendor=v.vendor,
        product=v.product,
        severity=v.severity.value,
        patched=v.patched,
        attack_vectors=[av.value for av in v.attack_vectors],
        description=v.description,
        impact=v.impact,
        mitigation=v.mitigation,
        cve=v.cve,
        disclosed=v.disclosed,
        patch_note=v.patch_note,
        references=v.references,
    )


def _finding_to_out(f) -> FindingOut:
    v = f.vulnerability
    return FindingOut(
        id=v.vid,
        name=v.name,
        vendor=v.vendor,
        product=v.product,
        severity=v.severity.value,
        detected=f.detected,
        confidence=f.confidence,
        patched=v.patched,
        description=v.description,
        mitigation=v.mitigation,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        vulndb_count=len(VULNERABILITIES),
    )


@app.get("/vulns", response_model=list[VulnSummary])
async def list_vulns(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    unpatched: bool = Query(False, description="Only unpatched"),
):
    results = list(VULNERABILITIES)
    if severity:
        results = [v for v in results if v.severity.value == severity.lower()]
    if vendor:
        results = [v for v in results if v.vendor.lower() == vendor.lower()]
    if unpatched:
        results = [v for v in results if not v.patched]
    return [_vuln_to_summary(v) for v in results]


@app.get("/vulns/{vid}", response_model=VulnDetail)
async def get_vuln(vid: str):
    v = get_vulnerability(vid)
    if v is None:
        raise HTTPException(status_code=404, detail=f"Vulnerability {vid} not found")
    return _vuln_to_detail(v)


@app.get("/vulns/vendor/{vendor}", response_model=list[VulnDetail])
async def get_vulns_by_vendor(vendor: str):
    results = get_by_vendor(vendor)
    if not results:
        raise HTTPException(status_code=404, detail=f"No vulnerabilities for vendor: {vendor}")
    return [_vuln_to_detail(v) for v in results]


@app.get("/vulns/severity/{level}", response_model=list[VulnDetail])
async def get_vulns_by_severity(level: str):
    try:
        sev = Severity(level.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {level}")
    results = get_by_severity(sev)
    return [_vuln_to_detail(v) for v in results]


@app.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest):
    report = scan_extensions(request.extensions, target_name=request.target)
    return ScanResponse(
        scan_id=report.scan_id,
        timestamp=report.timestamp,
        target=report.target,
        risk_score=round(report.risk_score, 1),
        risk_level=get_risk_level(report.risk_score),
        summary=report.summary,
        findings=[_finding_to_out(f) for f in report.findings],
    )


@app.post("/audit", response_model=ScanResponse)
async def audit():
    report = scan_all()
    return ScanResponse(
        scan_id=report.scan_id,
        timestamp=report.timestamp,
        target=report.target,
        risk_score=round(report.risk_score, 1),
        risk_level=get_risk_level(report.risk_score),
        summary=report.summary,
        findings=[_finding_to_out(f) for f in report.findings],
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    vendors = sorted(set(v.vendor for v in VULNERABILITIES))
    return StatsResponse(
        total_vulnerabilities=len(VULNERABILITIES),
        unpatched=len(get_unpatched()),
        critical=len([v for v in VULNERABILITIES if v.severity == Severity.CRITICAL]),
        high=len([v for v in VULNERABILITIES if v.severity == Severity.HIGH]),
        medium=len([v for v in VULNERABILITIES if v.severity == Severity.MEDIUM]),
        low=len([v for v in VULNERABILITIES if v.severity == Severity.LOW]),
        info=len([v for v in VULNERABILITIES if v.severity == Severity.INFO]),
        vendors=vendors,
        attack_vectors=[av.value for av in get_attack_vectors()],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
