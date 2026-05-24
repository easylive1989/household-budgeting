"""Export monthly aggregates from Notion to docs/data.json for GitHub Pages."""

import json
from pathlib import Path

TARGET_CATEGORIES = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]


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
