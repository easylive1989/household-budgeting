"""Export monthly aggregates from Notion to docs/data.json for GitHub Pages."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import calendar
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from common.notion import NotionApi

TARGET_CATEGORIES = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]
LEDGER_DB_ID = "43c59e00321e49a69d85037f0f45ba7e"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "data.json"


def aggregate_month(rows):
    """Given Notion page dicts for one month, return {by_category, by_funds, total}.

    Only transactions whose 分類 is in TARGET_CATEGORIES are counted.
    All amounts are converted to positive (expense is recorded as negative in Notion).
    """
    by_category = {c: 0 for c in TARGET_CATEGORIES}
    by_funds = {f: 0 for f in FUND_FIELDS}

    for row in rows:
        props = row["properties"]
        category = props["分類"]["select"]["name"]
        if category not in TARGET_CATEGORIES:
            continue

        for field in FUND_FIELDS:
            value = props.get(field, {}).get("number") or 0
            amount = abs(value)
            by_category[category] += amount
            by_funds[field] += amount

    total = sum(by_category.values())
    return {"by_category": by_category, "by_funds": by_funds, "total": total}


def load_existing_data(path):
    """Read existing data.json or return empty skeleton if file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return {
            "generated_at": None,
            "categories": list(TARGET_CATEGORIES),
            "members": ["Paul", "Lily"],
            "months": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def merge_month(data, yyyymm, month_agg):
    """Insert or overwrite the given month's aggregate in data['months']."""
    data["months"][yyyymm] = month_agg


def save_data(path, data):
    """Write data as pretty-printed JSON (ensure_ascii=False for Chinese)."""
    path = Path(path)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _last_month_range(today):
    """Return (start_iso, end_iso, yyyymm) for the month before `today`."""
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    start = datetime.combine(first, time.min) - timedelta(seconds=1)
    end = datetime.combine(last, time.max)
    return start.isoformat(), end.isoformat(), f"{year}{month:02d}"


def _build_filter(start_iso, end_iso):
    """Build the Notion query filter for the target categories within [start, end]."""
    # Task 5 verified: bare `date` filter works on the formula-typed `時間` property
    # for notion-client v2.x. If migrating to v3+, switch to {"formula": {"date": ...}}.
    return {
        "filter": {
            "and": [
                {"property": "時間", "date": {"after": start_iso}},
                {"property": "時間", "date": {"before": end_iso}},
                {
                    "or": [
                        {"property": "分類", "select": {"equals": c}}
                        for c in TARGET_CATEGORIES
                    ]
                },
            ]
        }
    }


def main(output_path=DEFAULT_OUTPUT):
    token = os.environ["NOTION_SECRET"]
    api = NotionApi(token)

    start_iso, end_iso, yyyymm = _last_month_range(date.today())
    resp = api.query_database(LEDGER_DB_ID, _build_filter(start_iso, end_iso))
    rows = resp.json()["results"]

    month_agg = aggregate_month(rows)
    data = load_existing_data(output_path)
    merge_month(data, yyyymm, month_agg)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    save_data(output_path, data)
    print(f"Exported {yyyymm}: total={month_agg['total']}")


if __name__ == "__main__":
    main()
