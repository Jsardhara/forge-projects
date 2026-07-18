"""End-to-end CLI tests for costrecon."""

import json

from costrecon.cli import main

CUR = """identity/LineItemId,lineItem/UsageAccountId,product/ProductName,lineItem/ProductCode,lineItem/Region,lineItem/UsageType,lineItem/LineItemDescription,lineItem/UnblendedCost,lineItem/UsageQuantity,lineItem/ResourceId,lineItem/UsageStartDate,lineItem/UsageEndDate
l1,123,Amazon Elastic Compute Cloud,EC2,us-east-1,BoxUsage,ec2,10.50,10,i-abc,2026-07-01,2026-07-31
l2,123,Amazon Simple Storage Service,S3,us-east-1,TimedStorage,s3,2.25,5,,2026-07-01,2026-07-31
"""

EST_MATCH = """key,estimated_cost,note
Amazon Elastic Compute Cloud,10.50,
Amazon Simple Storage Service,2.25,
"""

EST_MISMATCH = """key,estimated_cost,note
Amazon Elastic Compute Cloud,5.00,
Amazon Simple Storage Service,2.25,
"""

UTIL = """resource_id,type,utilization_pct,monthly_cost,region,state,age_days
i-idle,ec2,1.0,100.0,us-east-1,,
vol-1,ebs,,20.0,us-east-1,unattached,
eip-1,eip,,5.0,us-east-1,available,
snap-1,snapshot,,2.0,us-east-1,,90
i-ok,ec2,50.0,100.0,us-east-1,,
"""


def _w(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_cli_reconcile_json_clean(tmp_path, capsys):
    cur = _w(tmp_path, "cur.csv", CUR)
    est = _w(tmp_path, "est.csv", EST_MATCH)
    rc = main(["reconcile", "--cur", cur, "--estimates", est, "--format", "json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total_estimated"] == 12.75
    assert out["total_actual"] == 12.75
    assert out["anomaly_count"] == 0


def test_cli_reconcile_strict_fails_on_anomaly(tmp_path, capsys):
    cur = _w(tmp_path, "cur.csv", CUR)
    est = _w(tmp_path, "est.csv", EST_MISMATCH)
    rc = main(["reconcile", "--cur", cur, "--estimates", est, "--strict", "--format", "json"])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["anomaly_count"] >= 1


def test_cli_idle_json_findings(tmp_path, capsys):
    util = _w(tmp_path, "util.csv", UTIL)
    rc = main(["idle", "--utilization", util, "--format", "json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["finding_count"] == 4
    assert abs(out["total_savings"] - (99.0 + 20.0 + 5.0 + 1.3334)) < 0.01


def test_cli_idle_strict_fails_on_findings(tmp_path, capsys):
    util = _w(tmp_path, "util.csv", UTIL)
    rc = main(["idle", "--utilization", util, "--strict"])
    assert rc == 1


def test_cli_audit_combined(tmp_path, capsys):
    cur = _w(tmp_path, "cur.csv", CUR)
    est = _w(tmp_path, "est.csv", EST_MATCH)
    util = _w(tmp_path, "util.csv", UTIL)
    rc = main(["audit", "--cur", cur, "--estimates", est, "--utilization", util, "--format", "json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "reconciliation" in out and "idle" in out
    assert out["idle"]["finding_count"] == 4


def test_cli_missing_file_returns_2(tmp_path, capsys):
    rc = main(["reconcile", "--cur", "nope.csv", "--estimates", "nope.csv"])
    assert rc == 2


def test_cli_cur_missing_cost_returns_2(tmp_path, capsys):
    bad = _w(tmp_path, "bad.csv", "Service,Region\nEC2,us-east-1\n")
    est = _w(tmp_path, "est.csv", EST_MATCH)
    rc = main(["reconcile", "--cur", bad, "--estimates", est])
    assert rc == 2


def test_cli_no_subcommand_errors(tmp_path, capsys):
    import pytest

    with pytest.raises(SystemExit):
        main([])
