"""Export monthly aggregates from Notion to docs/data.json for GitHub Pages."""

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
