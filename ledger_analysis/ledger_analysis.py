import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.notion import NotionApi
import datetime
import calendar


notion_secret = os.getenv('NOTION_SECRET')
if not notion_secret:
    raise ValueError("請設定 NOTION_SECRET 環境變數")
notion_api = NotionApi(notion_secret)

DRY_RUN = os.getenv('DRY_RUN', '').lower() in ('1', 'true', 'yes')
if DRY_RUN:
    print("=== DRY RUN：不會實際寫入任何 Notion DB ===")

today = datetime.date.today()

# 計算上個月
if today.month == 1:
    last_month_year = today.year - 1
    last_month = 12
else:
    last_month_year = today.year
    last_month = today.month - 1

first_day_of_last_month = datetime.date(last_month_year, last_month, 1)
month_range = calendar.monthrange(first_day_of_last_month.year, first_day_of_last_month.month)[1]
last_day_of_last_month = first_day_of_last_month + datetime.timedelta(days=month_range-1)

# 計算時間區間：起始時間為上個月第一天減一秒，終止時間為上個月最後一天的最後一秒
start_datetime = datetime.datetime.combine(first_day_of_last_month, datetime.time.min) - datetime.timedelta(seconds=1)
end_datetime = datetime.datetime.combine(last_day_of_last_month, datetime.time.max)

# 下個月（實際上是這個月）
next_month_year = today.year
next_month = today.month

print(start_datetime)
print(end_datetime)

# 圓餅圖分析用的查詢（特定分類）
filter_body_chart = {
    "filter": {
        "and": [
            {
                "property": "時間",
                "date": {
                    "after": start_datetime.isoformat()
                }
            },
            {
                "property": "時間",
                "date": {
                    "before": end_datetime.isoformat()
                }
            },
            {
                "or": [
                    {
                        "property": "分類",
                        "select": {
                            "equals": "娛樂"
                        }
                    },
                    {
                        "property": "分類",
                        "select": {
                            "equals": "飲食"
                        }
                    },
                    {
                        "property": "分類",
                        "select": {
                            "equals": "日常用品"
                        }
                    },
                    {
                        "property": "分類",
                        "select": {
                            "equals": "水電管理費"
                        }
                    }
                ],
            }
        ]
    }
}

# 開帳關帳用的查詢（所有交易）
filter_body_all = {
    "filter": {
        "and": [
            {
                "property": "時間",
                "date": {
                    "after": start_datetime.isoformat()
                }
            },
            {
                "property": "時間",
                "date": {
                    "before": end_datetime.isoformat()
                }
            }
        ]
    }
}

# 查詢圓餅圖數據
response_chart = notion_api.query_database('43c59e00321e49a69d85037f0f45ba7e', filter_body_chart)
results_chart = response_chart.json()["results"]

# 查詢所有交易數據
response_all = notion_api.query_database('43c59e00321e49a69d85037f0f45ba7e', filter_body_all)
results_all = response_all.json()["results"]
#print(results)

# 分類 + 資金統計（以 abs 值累加，跟 backfill / export_json 一致）
CATEGORY_FIELDS = ["娛樂", "飲食", "日常用品", "水電管理費"]
FUND_FIELDS = ["Paul", "Lily", "現金", "銀行存款"]

by_category = {c: 0 for c in CATEGORY_FIELDS}
by_funds = {f: 0 for f in FUND_FIELDS}

for result in results_chart:
    catalog = result["properties"]["分類"]["select"]["name"]
    if catalog not in by_category:
        continue
    for field in FUND_FIELDS:
        value = result["properties"].get(field, {}).get("number") or 0
        amount = abs(value)
        by_category[catalog] += amount
        by_funds[field] += amount
    print(f"分析數據 - {catalog}: " + ", ".join(
        f"({f}: {result['properties'].get(f, {}).get('number') or 0})" for f in FUND_FIELDS
    ))

total_expense = sum(by_category.values())
print(f"分類統計: {by_category}")
print(f"資金統計: {by_funds}")
print(f"總額: {total_expense}")

# 開帳關帳統計（所有交易的總和）
total_paul = 0
total_lily = 0
total_cash = 0
total_bank = 0

for result in results_all:
    catalog = result["properties"]["分類"]["select"]["name"]

    paul = 0 if result["properties"]["Paul"]["number"] is None else result["properties"]["Paul"]["number"]
    lily = 0 if result["properties"]["Lily"]["number"] is None else result["properties"]["Lily"]["number"]
    cash = 0 if result["properties"]["現金"]["number"] is None else result["properties"]["現金"]["number"]
    bank = 0 if result["properties"]["銀行存款"]["number"] is None else result["properties"]["銀行存款"]["number"]
    
    # 累計所有交易的總和
    total_paul += paul
    total_lily += lily
    total_cash += cash
    total_bank += bank
    
    print(f"開帳關帳數據 - {catalog}: (paul: {paul}), (lily: {lily}), (cash: {cash}), (bank: {bank})")

title = first_day_of_last_month.strftime("%Y%m")

# 寫入新的分析結果 DB（結構化欄位，不含 Mermaid block）
result_database_id = '36a8303f78f780d2886bc082a46a51dd'
result_title_props = notion_api.get_property_names_by_type(result_database_id, ['title'])
result_title_prop = result_title_props['title']

page_properties = {
    result_title_prop: {"title": [{"text": {"content": title}}]},
    "總額": {"number": total_expense},
}
for c in CATEGORY_FIELDS:
    page_properties[c] = {"number": by_category[c]}
for f in FUND_FIELDS:
    page_properties[f] = {"number": by_funds[f]}

if notion_api.check_record_exists(result_database_id, result_title_prop, title):
    print(f"分析結果頁面 '{title}' 已存在，跳過創建")
elif DRY_RUN:
    print(f"[DRY RUN] 會創建分析結果頁面: {title} → {page_properties}")
else:
    create_response = notion_api.create_page(result_database_id, page_properties)
    if create_response.status_code == 200:
        print(f"成功創建分析結果頁面: {title}")
    else:
        print(f"創建分析結果頁面失敗: {create_response.status_code}")
        print(create_response.text)

# 自動偵測帳本資料庫的屬性名稱
ledger_database_id = '43c59e00321e49a69d85037f0f45ba7e'
ledger_props = notion_api.get_property_names_by_type(ledger_database_id, ['title'])

# 創建關帳記錄（沖銷歸零）
close_title = f"{title} 關帳"
close_properties = {
    ledger_props['title']: {
        "title": [
            {
                "text": {
                    "content": close_title
                }
            }
        ]
    },
    "分類": {
        "select": {
            "name": "財務整理"
        }
    },
    "Paul": {
        "number": -total_paul
    },
    "Lily": {
        "number": -total_lily
    },
    "現金": {
        "number": -total_cash
    },
    "銀行存款": {
        "number": -total_bank
    }
}

# 創建開帳記錄（下月開帳）
next_month_title = f"{next_month_year}{next_month:02d} 開帳"
open_properties = {
    ledger_props['title']: {
        "title": [
            {
                "text": {
                    "content": next_month_title
                }
            }
        ]
    },
    "分類": {
        "select": {
            "name": "財務整理"
        }
    },
    "Paul": {
        "number": total_paul
    },
    "Lily": {
        "number": total_lily
    },
    "現金": {
        "number": total_cash
    },
    "銀行存款": {
        "number": total_bank
    }
}

# 檢查關帳記錄是否已存在
if notion_api.check_record_exists(ledger_database_id, ledger_props['title'], close_title):
    print(f"關帳記錄 '{close_title}' 已存在，跳過創建")
elif DRY_RUN:
    print(f"[DRY RUN] 會創建關帳記錄: {close_title} (Paul: {-total_paul}, Lily: {-total_lily}, 現金: {-total_cash}, 銀行: {-total_bank})")
else:
    # 創建關帳記錄
    close_response = notion_api.create_page(ledger_database_id, close_properties)
    if close_response.status_code == 200:
        print(f"成功創建關帳記錄: {close_title}")
    else:
        print(f"創建關帳記錄失敗: {close_response.status_code}")
        print(close_response.text)

# 檢查開帳記錄是否已存在
if notion_api.check_record_exists(ledger_database_id, ledger_props['title'], next_month_title):
    print(f"開帳記錄 '{next_month_title}' 已存在，跳過創建")
elif DRY_RUN:
    print(f"[DRY RUN] 會創建開帳記錄: {next_month_title} (Paul: {total_paul}, Lily: {total_lily}, 現金: {total_cash}, 銀行: {total_bank})")
else:
    # 創建開帳記錄
    open_response = notion_api.create_page(ledger_database_id, open_properties)
    if open_response.status_code == 200:
        print(f"成功創建開帳記錄: {next_month_title}")
    else:
        print(f"創建開帳記錄失敗: {open_response.status_code}")
        print(open_response.text)

print(f"當月各項總額 - Paul: {total_paul}, Lily: {total_lily}, 現金: {total_cash}, 銀行存款: {total_bank}")
print(f"關帳金額 - Paul: {-total_paul}, Lily: {-total_lily}, 現金: {-total_cash}, 銀行存款: {-total_bank}")
print(f"開帳金額 - Paul: {total_paul}, Lily: {total_lily}, 現金: {total_cash}, 銀行存款: {total_bank}")