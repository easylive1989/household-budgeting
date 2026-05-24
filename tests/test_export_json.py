import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from ledger_analysis.export_json import (
    aggregate_month,
    fetch_all_pages,
    save_data,
)


def _row(category, paul=None, lily=None, cash=None, bank=None, time_start=None):
    """Helper: build a fake Notion page dict matching the schema."""
    props = {
        "分類": {"select": {"name": category}},
        "Paul": {"number": paul},
        "Lily": {"number": lily},
        "現金": {"number": cash},
        "銀行存款": {"number": bank},
    }
    if time_start is not None:
        props["時間"] = {"formula": {"date": {"start": time_start}}}
    return {"properties": props}


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


def test_save_data_writes_json_with_indent(tmp_path):
    f = tmp_path / "out.json"
    data = {"months": {"202504": {"total": 500}}}

    save_data(f, data)

    loaded = json.loads(f.read_text())
    assert loaded == data
    # Should be human-readable (indented)
    assert "\n  " in f.read_text()


def test_fetch_all_pages_single_page():
    """When Notion returns has_more=False, query_database is called exactly once."""
    api = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {
        "results": [{"id": "a"}, {"id": "b"}],
        "has_more": False,
        "next_cursor": None,
    }
    api.query_database.return_value = resp

    rows = fetch_all_pages(api, "db-id", {"filter": {"foo": "bar"}})

    assert rows == [{"id": "a"}, {"id": "b"}]
    assert api.query_database.call_count == 1
    # First call should not carry a start_cursor
    _, first_payload = api.query_database.call_args_list[0][0]
    assert "start_cursor" not in first_payload


def test_fetch_all_pages_multi_page_follows_cursor():
    """Pagination: keep calling until has_more is False, passing next_cursor each time."""
    api = MagicMock()

    resp1 = MagicMock()
    resp1.json.return_value = {
        "results": [{"id": "a"}],
        "has_more": True,
        "next_cursor": "cursor-1",
    }
    resp2 = MagicMock()
    resp2.json.return_value = {
        "results": [{"id": "b"}],
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    resp3 = MagicMock()
    resp3.json.return_value = {
        "results": [{"id": "c"}],
        "has_more": False,
        "next_cursor": None,
    }
    api.query_database.side_effect = [resp1, resp2, resp3]

    rows = fetch_all_pages(api, "db-id", {"filter": {"foo": "bar"}})

    assert rows == [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert api.query_database.call_count == 3

    # Inspect each call's payload
    payloads = [call[0][1] for call in api.query_database.call_args_list]
    assert "start_cursor" not in payloads[0]
    assert payloads[1]["start_cursor"] == "cursor-1"
    assert payloads[2]["start_cursor"] == "cursor-2"
    # Filter should be preserved on every call
    for p in payloads:
        assert p["filter"] == {"foo": "bar"}


def test_main_fetches_all_pages_groups_by_month_writes_json(tmp_path, monkeypatch):
    """End-to-end main(): paginated Notion response → grouped months → JSON file."""
    monkeypatch.setenv("NOTION_SECRET", "fake-token")

    page1_rows = [
        {"properties": {
            "分類": {"select": {"name": "飲食"}},
            "Paul": {"number": -1000},
            "Lily": {"number": None},
            "現金": {"number": None},
            "銀行存款": {"number": None},
            "時間": {"formula": {"date": {"start": "2025-04-15T10:00:00.000+00:00"}}},
        }},
        {"properties": {
            "分類": {"select": {"name": "娛樂"}},
            "Paul": {"number": None},
            "Lily": {"number": -300},
            "現金": {"number": None},
            "銀行存款": {"number": None},
            "時間": {"formula": {"date": {"start": "2025-04-20T10:00:00.000+00:00"}}},
        }},
    ]
    page2_rows = [
        {"properties": {
            "分類": {"select": {"name": "日常用品"}},
            "Paul": {"number": None},
            "Lily": {"number": None},
            "現金": {"number": -200},
            "銀行存款": {"number": None},
            "時間": {"formula": {"date": {"start": "2025-05-01T10:00:00.000+00:00"}}},
        }},
    ]

    output_path = tmp_path / "data.json"

    with patch("ledger_analysis.export_json.NotionApi") as MockApi:
        mock_api = MagicMock()
        MockApi.return_value = mock_api

        resp1 = MagicMock()
        resp1.json.return_value = {
            "results": page1_rows,
            "has_more": True,
            "next_cursor": "cursor-1",
        }
        resp2 = MagicMock()
        resp2.json.return_value = {
            "results": page2_rows,
            "has_more": False,
            "next_cursor": None,
        }
        mock_api.query_database.side_effect = [resp1, resp2]

        from ledger_analysis.export_json import main
        main(output_path)

    # Verify pagination happened: two calls, second has start_cursor
    assert mock_api.query_database.call_count == 2
    second_call_payload = mock_api.query_database.call_args_list[1][0][1]
    assert second_call_payload["start_cursor"] == "cursor-1"

    result = json.loads(output_path.read_text())
    assert result["categories"] == ["娛樂", "飲食", "日常用品", "水電管理費"]
    assert result["members"] == ["Paul", "Lily"]
    assert result["generated_at"] is not None

    # Both months should be present and aggregated correctly
    assert "202504" in result["months"]
    assert "202505" in result["months"]

    apr = result["months"]["202504"]
    assert apr["by_category"]["飲食"] == 1000
    assert apr["by_category"]["娛樂"] == 300
    assert apr["by_funds"]["Paul"] == 1000
    assert apr["by_funds"]["Lily"] == 300
    assert apr["total"] == 1300

    may = result["months"]["202505"]
    assert may["by_category"]["日常用品"] == 200
    assert may["by_funds"]["現金"] == 200
    assert may["total"] == 200
