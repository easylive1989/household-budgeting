import json
from unittest.mock import patch, MagicMock

from ledger_analysis.export_sheet import (
    HEADER,
    build_rows,
    fetch_all_pages,
    page_to_month_entry,
)


CATEGORIES = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUNDS = ["Paul", "Lily", "現金", "銀行存款"]


def _make_page(title, by_category=None, by_funds=None, total=0, title_prop_name="月份"):
    """Helper: build a fake Notion analysis-DB page with the expected shape."""
    by_category = by_category or {}
    by_funds = by_funds or {}
    props = {
        title_prop_name: {
            "type": "title",
            "title": [{"plain_text": title}],
        },
        "總額": {"type": "number", "number": total},
    }
    for c in CATEGORIES:
        props[c] = {"type": "number", "number": by_category.get(c, 0)}
    for f in FUNDS:
        props[f] = {"type": "number", "number": by_funds.get(f, 0)}
    return {"properties": props}


def test_page_to_month_entry_extracts_yyyymm_and_numbers():
    page = _make_page(
        "202504",
        by_category={"飲食": 1000, "娛樂": 300},
        by_funds={"Paul": 800, "Lily": 500},
        total=1300,
    )

    yyyymm, entry = page_to_month_entry(page)

    assert yyyymm == "202504"
    assert entry["by_category"] == {"娛樂": 300, "飲食": 1000, "日常用品": 0, "水電管理費": 0}
    assert entry["by_funds"] == {"Paul": 800, "Lily": 500, "現金": 0, "銀行存款": 0}
    assert entry["total"] == 1300


def test_page_to_month_entry_skips_non_yyyymm_title():
    assert page_to_month_entry(_make_page("Random Page")) is None
    assert page_to_month_entry(_make_page("2025-04")) is None  # length 7
    assert page_to_month_entry(_make_page("20250")) is None    # length 5


def test_page_to_month_entry_skips_empty_title():
    assert page_to_month_entry(_make_page("")) is None


def test_page_to_month_entry_handles_null_numbers():
    page = _make_page("202504")
    page["properties"]["飲食"]["number"] = None
    page["properties"]["總額"]["number"] = None

    _, entry = page_to_month_entry(page)

    assert entry["by_category"]["飲食"] == 0
    assert entry["total"] == 0


def test_page_to_month_entry_finds_title_under_any_property_name():
    """Title property can be named anything — code locates it by type, not name."""
    page = _make_page("202504", title_prop_name="自訂欄位名稱")
    yyyymm, _ = page_to_month_entry(page)
    assert yyyymm == "202504"


def test_fetch_all_pages_single_page():
    api = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {
        "results": [{"id": "a"}, {"id": "b"}],
        "has_more": False,
        "next_cursor": None,
    }
    api.query_database.return_value = resp

    rows = fetch_all_pages(api, "db-id")

    assert rows == [{"id": "a"}, {"id": "b"}]
    assert api.query_database.call_count == 1
    first_payload = api.query_database.call_args_list[0][0][1]
    assert "start_cursor" not in first_payload


def test_fetch_all_pages_multi_page_follows_cursor():
    api = MagicMock()
    resp1 = MagicMock()
    resp1.json.return_value = {
        "results": [{"id": "a"}], "has_more": True, "next_cursor": "c1",
    }
    resp2 = MagicMock()
    resp2.json.return_value = {
        "results": [{"id": "b"}], "has_more": True, "next_cursor": "c2",
    }
    resp3 = MagicMock()
    resp3.json.return_value = {
        "results": [{"id": "c"}], "has_more": False, "next_cursor": None,
    }
    api.query_database.side_effect = [resp1, resp2, resp3]

    rows = fetch_all_pages(api, "db-id")

    assert rows == [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert api.query_database.call_count == 3
    payloads = [c[0][1] for c in api.query_database.call_args_list]
    assert "start_cursor" not in payloads[0]
    assert payloads[1]["start_cursor"] == "c1"
    assert payloads[2]["start_cursor"] == "c2"


def test_header_matches_spec():
    assert HEADER == ["月份", "娛樂", "飲食", "日常用品", "水電管理費",
                      "Paul", "Lily", "現金", "銀行存款", "總額"]


def test_build_rows_sorted_by_month_with_column_order():
    months = {
        "202505": {"by_category": {"娛樂": 1, "飲食": 2, "日常用品": 3, "水電管理費": 4},
                   "by_funds": {"Paul": 5, "Lily": 6, "現金": 7, "銀行存款": 8}, "total": 10},
        "202412": {"by_category": {"娛樂": 0, "飲食": 0, "日常用品": 0, "水電管理費": 0},
                   "by_funds": {"Paul": 0, "Lily": 0, "現金": 0, "銀行存款": 0}, "total": 0},
    }
    assert build_rows(months) == [
        ["202412", 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ["202505", 1, 2, 3, 4, 5, 6, 7, 8, 10],
    ]


def test_build_rows_empty():
    assert build_rows({}) == []
