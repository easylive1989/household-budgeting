"""Export monthly aggregates from Notion to docs/data.json for GitHub Pages."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from collections import defaultdict
from datetime import date, datetime, timezone
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


def save_data(path, data):
    """Write data as pretty-printed JSON (ensure_ascii=False for Chinese)."""
    path = Path(path)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_filter_all():
    """Build the Notion query filter for the target categories (no date range)."""
    return {
        "filter": {
            "or": [
                {"property": "分類", "select": {"equals": c}}
                for c in TARGET_CATEGORIES
            ]
        }
    }


def fetch_all_pages(api, db_id, filter_body):
    """Fetch all rows from Notion, transparently following pagination cursors."""
    all_rows = []
    payload = dict(filter_body)
    while True:
        resp = api.query_database(db_id, payload)
        data = resp.json()
        all_rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
        payload = dict(filter_body)
        payload["start_cursor"] = next_cursor
    return all_rows


def _extract_yyyymm(row):
    """Pull 'YYYYMM' from row['properties']['時間']['formula']['date']['start']."""
    start = row["properties"]["時間"]["formula"]["date"]["start"]
    # ISO-8601 like "2025-04-15T10:00:00.000+00:00" — first 7 chars give YYYY-MM
    return start[:4] + start[5:7]


def main(output_path=DEFAULT_OUTPUT):
    token = os.environ["NOTION_SECRET"]
    api = NotionApi(token)

    rows = fetch_all_pages(api, LEDGER_DB_ID, _build_filter_all())

    # Exclude the current (in-progress) month and any future-dated months —
    # partial-month totals are misleading next to fully-closed months.
    today = date.today()
    current_yyyymm = f"{today.year}{today.month:02d}"

    grouped = defaultdict(list)
    for row in rows:
        try:
            yyyymm = _extract_yyyymm(row)
        except (KeyError, TypeError):
            # Skip rows without a parseable 時間 formula
            continue
        if yyyymm >= current_yyyymm:
            continue
        grouped[yyyymm].append(row)

    months = {ym: aggregate_month(rs) for ym, rs in grouped.items()}
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": list(TARGET_CATEGORIES),
        "members": ["Paul", "Lily"],
        "months": months,
    }
    save_data(output_path, data)
    print(
        f"Exported {len(months)} months from {len(rows)} rows: "
        f"{sorted(months.keys())}"
    )


if __name__ == "__main__":
    main()
