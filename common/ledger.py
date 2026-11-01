import datetime

TAIPEI = datetime.timezone(datetime.timedelta(hours=8))


def close_timestamp(last_day):
    """關帳記錄的時間：該日台灣時間的最後一秒（ISO 8601，帶時區）。"""
    return datetime.datetime.combine(
        last_day, datetime.time(23, 59, 59), tzinfo=TAIPEI
    ).isoformat()


def is_close_record(page, close_title):
    """判斷帳本 page 是否為指定的關帳記錄。"""
    for prop in page["properties"].values():
        if prop.get("type") == "title":
            text = "".join(part.get("plain_text", "") for part in prop["title"])
            return text == close_title
    return False
