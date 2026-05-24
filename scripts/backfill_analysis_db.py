"""把帳本 DB 的歷史月份彙總 backfill 到新的分析結果 DB。

來源：帳本 DB（43c59e00...），撈四大分類所有交易，依月份分組（排除當月與未來），
每月寫一筆結構化頁面到新 DB（36a8303f...）。

可重複執行：已存在的月份會跳過。
"""

import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.notion import NotionApi


LEDGER_DB_ID = "43c59e00321e49a69d85037f0f45ba7e"
NEW_ANALYSIS_DB_ID = "36a8303f78f780d2886bc082a46a51dd"

CATEGORY_FIELDS = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]
TOTAL_FIELD = "總額"


def build_category_filter():
    """只撈四大分類的交易。"""
    return {
        "filter": {
            "or": [
                {"property": "分類", "select": {"equals": c}}
                for c in CATEGORY_FIELDS
            ]
        }
    }


def fetch_all_pages(api, db_id, filter_body):
    """透明處理 Notion 的分頁 cursor。"""
    rows = []
    payload = dict(filter_body)
    while True:
        resp = api.query_database(db_id, payload)
        data = resp.json()
        rows.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
        payload = dict(filter_body)
        payload["start_cursor"] = next_cursor
    return rows


def extract_yyyymm(row):
    """從 properties.時間.formula.date.start 取 YYYYMM。"""
    start = row["properties"]["時間"]["formula"]["date"]["start"]
    return start[:4] + start[5:7]


def aggregate(rows):
    """回傳 (by_category, by_funds, total)，金額都取 abs()。"""
    by_category = {c: 0 for c in CATEGORY_FIELDS}
    by_funds = {f: 0 for f in FUND_FIELDS}
    for row in rows:
        props = row["properties"]
        category = props["分類"]["select"]["name"]
        if category not in CATEGORY_FIELDS:
            continue
        for field in FUND_FIELDS:
            value = props.get(field, {}).get("number") or 0
            amount = abs(value)
            by_category[category] += amount
            by_funds[field] += amount
    total = sum(by_category.values())
    return by_category, by_funds, total


def build_page_properties(title_prop_name, yyyymm, by_category, by_funds, total):
    props = {
        title_prop_name: {"title": [{"text": {"content": yyyymm}}]},
        TOTAL_FIELD: {"number": total},
    }
    for c in CATEGORY_FIELDS:
        props[c] = {"number": by_category[c]}
    for f in FUND_FIELDS:
        props[f] = {"number": by_funds[f]}
    return props


def main():
    token = os.environ.get("NOTION_SECRET")
    if not token:
        raise SystemExit("請設定 NOTION_SECRET 環境變數")

    api = NotionApi(token)

    title_props = api.get_property_names_by_type(NEW_ANALYSIS_DB_ID, ["title"])
    title_prop_name = title_props.get("title")
    if not title_prop_name:
        raise SystemExit("新 DB 找不到 title 欄位")

    print("撈取帳本資料...")
    rows = fetch_all_pages(api, LEDGER_DB_ID, build_category_filter())
    print(f"取得 {len(rows)} 筆交易")

    today = date.today()
    current_yyyymm = f"{today.year}{today.month:02d}"

    grouped = defaultdict(list)
    for row in rows:
        try:
            yyyymm = extract_yyyymm(row)
        except (KeyError, TypeError):
            continue
        if yyyymm >= current_yyyymm:
            continue
        grouped[yyyymm].append(row)

    print(f"涵蓋月份: {sorted(grouped.keys())}")

    created = 0
    skipped = 0
    failed = 0
    for yyyymm in sorted(grouped.keys()):
        if api.check_record_exists(NEW_ANALYSIS_DB_ID, title_prop_name, yyyymm):
            print(f"  {yyyymm}: 已存在，跳過")
            skipped += 1
            continue

        by_category, by_funds, total = aggregate(grouped[yyyymm])
        props = build_page_properties(title_prop_name, yyyymm, by_category, by_funds, total)
        resp = api.create_page(NEW_ANALYSIS_DB_ID, props)
        if resp.status_code == 200:
            print(f"  {yyyymm}: 建立成功 (total={total})")
            created += 1
        else:
            print(f"  {yyyymm}: 建立失敗 {resp.status_code} - {resp.text}")
            failed += 1

    print(f"\n完成: 新增 {created} 筆，跳過 {skipped} 筆，失敗 {failed} 筆")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
