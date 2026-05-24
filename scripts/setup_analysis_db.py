"""對新的分析結果 DB 加入結構化統計欄位。

可重複執行：Notion 對已存在且 spec 相同的欄位視為 no-op。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.notion import NotionApi


NEW_ANALYSIS_DB_ID = "36a8303f78f780d2886bc082a46a51dd"

CATEGORY_FIELDS = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]
TOTAL_FIELD = "總額"


def build_schema():
    """回傳 databases.update 用的 properties dict（全部都是 number 欄位）。"""
    schema = {}
    for name in CATEGORY_FIELDS + FUND_FIELDS + [TOTAL_FIELD]:
        schema[name] = {"number": {"format": "number"}}
    return schema


def main():
    token = os.environ.get("NOTION_SECRET")
    if not token:
        raise SystemExit("請設定 NOTION_SECRET 環境變數")

    api = NotionApi(token)
    schema = build_schema()
    resp = api.update_database_schema(NEW_ANALYSIS_DB_ID, schema)

    if resp.status_code == 200:
        print(f"成功更新 DB schema，加入 {len(schema)} 個欄位:")
        for name in schema:
            print(f"  - {name} (number)")
    else:
        print(f"更新 DB schema 失敗: {resp.status_code}")
        print(resp.text)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
