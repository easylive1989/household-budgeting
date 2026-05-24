import json
from pathlib import Path

from ledger_analysis.export_json import (
    aggregate_month,
    load_existing_data,
    merge_month,
    save_data,
)


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


def test_load_existing_data_returns_empty_skeleton_when_file_missing(tmp_path):
    data = load_existing_data(tmp_path / "missing.json")
    assert data == {
        "generated_at": None,
        "categories": ["娛樂", "飲食", "日常用品", "水電管理費"],
        "members": ["Paul", "Lily"],
        "months": {},
    }


def test_load_existing_data_reads_existing_file(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps({
        "generated_at": "2024-01-01",
        "categories": ["A"],
        "members": ["B"],
        "months": {"202312": {"total": 100}},
    }))

    data = load_existing_data(f)
    assert data["months"]["202312"]["total"] == 100


def test_merge_month_inserts_new_month():
    data = {"months": {}}
    month_agg = {"by_category": {"飲食": 500}, "by_funds": {"Paul": 500}, "total": 500}

    merge_month(data, "202504", month_agg)

    assert data["months"]["202504"] == month_agg


def test_merge_month_overwrites_existing_month():
    data = {"months": {"202504": {"total": 999}}}
    new_agg = {"by_category": {}, "by_funds": {}, "total": 500}

    merge_month(data, "202504", new_agg)

    assert data["months"]["202504"]["total"] == 500


def test_save_data_writes_json_with_indent(tmp_path):
    f = tmp_path / "out.json"
    data = {"months": {"202504": {"total": 500}}}

    save_data(f, data)

    loaded = json.loads(f.read_text())
    assert loaded == data
    # Should be human-readable (indented)
    assert "\n  " in f.read_text()
