"""Tests for CUR parsing."""

from costrecon.cur import parse_cur, summarize_by_service

CUR_FULL = """identity/LineItemId,lineItem/UsageAccountId,product/ProductName,lineItem/ProductCode,lineItem/Region,lineItem/UsageType,lineItem/LineItemDescription,lineItem/UnblendedCost,lineItem/UsageQuantity,lineItem/ResourceId,lineItem/UsageStartDate,lineItem/UsageEndDate
line-1,123456789012,Amazon Elastic Compute Cloud,EC2,us-east-1,BoxUsage:t3.micro,Running hours,10.50,100.0,i-abc,2026-07-01,2026-07-31
line-2,123456789012,Amazon Simple Storage Service,S3,us-east-1,TimedStorage-ByteHrs,Storage,2.25,50.0,,2026-07-01,2026-07-31
line-3,123456789012,Amazon Elastic Compute Cloud,EC2,us-east-1,BoxUsage:t3.micro,RI credit,-3.00,0.0,i-def,2026-07-01,2026-07-31
"""

CUR_SIMPLE = """Service,Region,cost,quantity,resource_id
EC2,us-east-1,7.50,10,i-abc
S3,us-east-1,2.25,5,
"""

CUR_NO_COST = """Service,Region,quantity
EC2,us-east-1,10
"""


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_parse_full_cur_returns_normalized_items(tmp_path):
    items = parse_cur(_write(tmp_path, "cur.csv", CUR_FULL))
    assert len(items) == 3
    assert items[0].service == "Amazon Elastic Compute Cloud"
    assert items[0].cost == 10.50
    assert items[0].account_id == "123456789012"


def test_parse_cur_marks_credits(tmp_path):
    items = parse_cur(_write(tmp_path, "cur.csv", CUR_FULL))
    credit = [i for i in items if i.cost < 0][0]
    assert credit.is_credit is True
    assert credit.resource_id == "i-def"


def test_summarize_by_service_sums_and_handles_credits(tmp_path):
    items = parse_cur(_write(tmp_path, "cur.csv", CUR_FULL))
    totals = summarize_by_service(items)
    # EC2 = 10.50 - 3.00 = 7.50 ; S3 = 2.25
    assert totals["Amazon Elastic Compute Cloud"] == 7.50
    assert totals["Amazon Simple Storage Service"] == 2.25
    assert round(sum(totals.values()), 2) == 9.75


def test_summarize_by_service_region_split(tmp_path):
    items = parse_cur(_write(tmp_path, "cur.csv", CUR_FULL))
    totals = summarize_by_service(items, split_region=True)
    assert "Amazon Elastic Compute Cloud|us-east-1" in totals
    assert "Amazon Simple Storage Service|us-east-1" in totals


def test_parse_simplified_schema(tmp_path):
    items = parse_cur(_write(tmp_path, "cur.csv", CUR_SIMPLE))
    assert len(items) == 2
    totals = summarize_by_service(items)
    assert totals["EC2"] == 7.50
    assert totals["S3"] == 2.25


def test_parse_cur_missing_cost_column_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        parse_cur(_write(tmp_path, "cur.csv", CUR_NO_COST))
