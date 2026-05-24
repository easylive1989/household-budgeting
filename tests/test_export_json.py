from ledger_analysis.export_json import aggregate_month


def _row(category, paul=None, lily=None, cash=None, bank=None):
    """Helper: build a fake Notion page dict matching the schema."""
    return {
        "properties": {
            "分類": {"select": {"name": category}},
            "Paul": {"number": paul},
            "Lily": {"number": lily},
            "現金": {"number": cash},
            "銀行存款": {"number": bank},
        }
    }


def test_aggregate_month_returns_by_category_by_funds_total():
    rows = [
        _row("飲食", bank=-1000),
        _row("飲食", paul=-500),
        _row("娛樂", lily=-300),
        _row("日常用品", cash=-200),
        _row("水電管理費", bank=-3000),
    ]

    result = aggregate_month(rows)

    assert result == {
        "by_category": {
            "飲食": 1500,
            "娛樂": 300,
            "日常用品": 200,
            "水電管理費": 3000,
        },
        "by_funds": {
            "Paul": 500,
            "Lily": 300,
            "現金": 200,
            "銀行存款": 4000,
        },
        "total": 5000,
    }


def test_aggregate_month_handles_null_number_fields():
    rows = [_row("飲食", paul=-500)]  # other 3 fields default to None

    result = aggregate_month(rows)

    assert result["by_category"]["飲食"] == 500
    assert result["by_funds"]["Paul"] == 500
    assert result["by_funds"]["Lily"] == 0
    assert result["by_funds"]["現金"] == 0
    assert result["by_funds"]["銀行存款"] == 0
    assert result["total"] == 500


def test_aggregate_month_ignores_unknown_categories():
    rows = [
        _row("飲食", paul=-500),
        _row("收入", paul=10000),
        _row("財務整理", paul=-99999),
    ]

    result = aggregate_month(rows)

    assert result["by_category"] == {
        "飲食": 500,
        "娛樂": 0,
        "日常用品": 0,
        "水電管理費": 0,
    }
    assert result["total"] == 500
    # Funds should also not include the filtered rows
    assert result["by_funds"]["Paul"] == 500


def test_aggregate_month_returns_zeros_for_missing_target_categories():
    """If a target category has no transactions that month, key should still be 0."""
    rows = [_row("飲食", paul=-500)]

    result = aggregate_month(rows)

    assert result["by_category"] == {
        "飲食": 500,
        "娛樂": 0,
        "日常用品": 0,
        "水電管理費": 0,
    }
