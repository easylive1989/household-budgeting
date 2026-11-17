"""Export monthly aggregates from the analysis DB to the「家庭月統計」Google Sheet tab.

Source: 分析結果 DB（36a8303f...）。每筆 row 就是一個月的結構化彙總，
直接讀 properties，不再做聚合。結果 POST 給試算表的 Apps Script Web App
（見 apps_script/），由它全量覆寫「家庭月統計」分頁。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.notion import NotionApi

CATEGORIES = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]
HEADER = ["月份", *CATEGORIES, *FUND_FIELDS, "總額"]
ANALYSIS_DB_ID = "36a8303f78f780d2886bc082a46a51dd"


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


def build_rows(months):
    """Turn {yyyymm: entry} into sheet rows ordered by month, columns as HEADER."""
    return [
        [
            yyyymm,
            *(months[yyyymm]["by_category"][c] for c in CATEGORIES),
            *(months[yyyymm]["by_funds"][f] for f in FUND_FIELDS),
            months[yyyymm]["total"],
        ]
        for yyyymm in sorted(months)
    ]
