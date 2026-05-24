"""Manual smoke test: verify that Notion API accepts the existing filter for
the formula-typed `時間` property. Run locally with NOTION_SECRET set.

Note: notion-client 3.x removed `databases.query` in favor of
`data_sources.query` (the Notion API itself deprecated database-level query).
We therefore exercise the filter shapes against the data source endpoint —
the filter body shape is what we're verifying here, not the endpoint."""
import os
import datetime
from notion_client import Client

client = Client(auth=os.environ["NOTION_SECRET"])
DB_ID = "43c59e00321e49a69d85037f0f45ba7e"

# Resolve the (single) data source under this database
db = client.databases.retrieve(database_id=DB_ID)
data_source_id = db["data_sources"][0]["id"]
print(f"Using data_source_id: {data_source_id}\n")

# Use a recent fixed range (last 30 days) to ensure some rows exist
now = datetime.datetime.now(datetime.timezone.utc)
after = (now - datetime.timedelta(days=30)).isoformat()
before = now.isoformat()

# Variant A: existing script syntax (might be invalid for formula property)
print("=== Variant A: bare date filter ===")
try:
    resp = client.data_sources.query(
        data_source_id=data_source_id,
        filter={
            "and": [
                {"property": "時間", "date": {"after": after}},
                {"property": "時間", "date": {"before": before}},
            ]
        },
    )
    print(f"Got {len(resp['results'])} results")
except Exception as e:
    print(f"FAILED: {e}")

# Variant B: nested formula.date filter (Notion API documented syntax)
print("\n=== Variant B: formula.date filter ===")
try:
    resp = client.data_sources.query(
        data_source_id=data_source_id,
        filter={
            "and": [
                {"property": "時間", "formula": {"date": {"after": after}}},
                {"property": "時間", "formula": {"date": {"before": before}}},
            ]
        },
    )
    print(f"Got {len(resp['results'])} results")
except Exception as e:
    print(f"FAILED: {e}")
