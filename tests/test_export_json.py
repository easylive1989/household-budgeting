import json
from unittest.mock import patch, MagicMock

from ledger_analysis.export_json import (
    fetch_all_pages,
    page_to_month_entry,
    save_data,
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


def test_save_data_writes_json_with_indent(tmp_path):
    f = tmp_path / "out.json"
    data = {"months": {"202504": {"total": 500}}}

    save_data(f, data)

    loaded = json.loads(f.read_text())
    assert loaded == data
    assert "\n  " in f.read_text()


def test_main_reads_pages_and_writes_json(tmp_path, monkeypatch):
    """End-to-end: paginated analysis-DB pages → JSON file, non-YYYYMM rows skipped."""
    monkeypatch.setenv("NOTION_SECRET", "fake-token")

    pages = [
        _make_page("202504", by_category={"飲食": 1000}, by_funds={"Paul": 1000}, total=1000),
        _make_page("Other Random Page"),  # should be skipped
        _make_page("202505", by_category={"娛樂": 500}, by_funds={"Lily": 500}, total=500),
    ]

    output_path = tmp_path / "data.json"

    with patch("ledger_analysis.export_json.NotionApi") as MockApi:
        mock_api = MagicMock()
        MockApi.return_value = mock_api
        resp = MagicMock()
        resp.json.return_value = {"results": pages, "has_more": False, "next_cursor": None}
        mock_api.query_database.return_value = resp

        from ledger_analysis.export_json import main
        main(output_path)

    result = json.loads(output_path.read_text())

    assert result["categories"] == CATEGORIES
    assert result["members"] == ["Paul", "Lily"]
    assert result["generated_at"] is not None
    assert set(result["months"].keys()) == {"202504", "202505"}
    assert result["months"]["202504"]["total"] == 1000
    assert result["months"]["202504"]["by_category"]["飲食"] == 1000
    assert result["months"]["202505"]["by_category"]["娛樂"] == 500
    assert result["months"]["202505"]["by_funds"]["Lily"] == 500
