"""Export monthly aggregates from the analysis DB to docs/data.json for GitHub Pages.

Source: 分析結果 DB（36a8303f...）。每筆 row 就是一個月的結構化彙總，
直接讀 properties，不再做聚合。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, timezone
from pathlib import Path

from common.notion import NotionApi

CATEGORIES = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]
ANALYSIS_DB_ID = "36a8303f78f780d2886bc082a46a51dd"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "data.json"


def fetch_all_pages(api, db_id):
    """Fetch all rows from the analysis DB, following pagination cursors."""
    rows = []
    payload = {}
    while True:
        resp = api.query_database(db_id, payload)
        data = resp.json()
        rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
        payload = {"start_cursor": next_cursor}
    return rows


def _title_text(prop):
    return "".join(part.get("plain_text", "") for part in (prop.get("title") or []))


def _num(prop):
    return prop.get("number") or 0


def page_to_month_entry(page):
    """Convert one analysis-DB page into (yyyymm, entry). Returns None to skip."""
    props = page["properties"]
    title_value = None
    for p in props.values():
        if p.get("type") == "title":
            title_value = _title_text(p)
            break
    # Only accept YYYYMM titles — skips any stray non-month rows
    if not title_value or len(title_value) != 6 or not title_value.isdigit():
        return None

    entry = {
        "by_category": {c: _num(props.get(c, {})) for c in CATEGORIES},
        "by_funds": {f: _num(props.get(f, {})) for f in FUND_FIELDS},
        "total": _num(props.get("總額", {})),
    }
    return title_value, entry


def save_data(path, data):
    path = Path(path)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(output_path=DEFAULT_OUTPUT):
    token = os.environ["NOTION_SECRET"]
    api = NotionApi(token)

    pages = fetch_all_pages(api, ANALYSIS_DB_ID)
    months = {}
    for page in pages:
        result = page_to_month_entry(page)
        if result is None:
            continue
        yyyymm, entry = result
        months[yyyymm] = entry

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": list(CATEGORIES),
        "members": ["Paul", "Lily"],
        "months": months,
    }
    save_data(output_path, data)
    print(
        f"Exported {len(months)} months from {len(pages)} pages: "
        f"{sorted(months.keys())}"
    )


if __name__ == "__main__":
    main()
