import datetime

from common.ledger import close_timestamp, is_close_record


def _page(title):
    return {
        "properties": {
            "Paul": {"type": "number", "number": 1},
            "名目": {"type": "title", "title": [{"plain_text": title}]},
        }
    }


def test_close_timestamp_is_last_second_of_day_in_taipei_time():
    assert close_timestamp(datetime.date(2026, 10, 31)) == "2026-10-31T23:59:59+08:00"


def test_close_timestamp_falls_inside_closed_month_and_outside_next_month():
    closed = datetime.datetime.fromisoformat(close_timestamp(datetime.date(2026, 10, 31)))
    # ledger_analysis.py 的查詢區間以不帶時區的字串表示，Notion 視為 UTC
    utc = datetime.timezone.utc
    october_end = datetime.datetime(2026, 10, 31, 23, 59, 59, 999999, tzinfo=utc)
    november_start = datetime.datetime(2026, 10, 31, 23, 59, 59, tzinfo=utc)
    assert closed < october_end
    assert not closed > november_start


def test_is_close_record_matches_exact_title():
    assert is_close_record(_page("202610 關帳"), "202610 關帳")


def test_is_close_record_ignores_other_records():
    assert not is_close_record(_page("202610 開帳"), "202610 關帳")
    assert not is_close_record(_page("202609 關帳"), "202610 關帳")
    assert not is_close_record(_page("高鐵票"), "202610 關帳")


def test_is_close_record_joins_multi_part_titles():
    page = {"properties": {"名目": {"type": "title", "title": [
        {"plain_text": "202610 "}, {"plain_text": "關帳"},
    ]}}}
    assert is_close_record(page, "202610 關帳")
