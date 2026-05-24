# Household Budgeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把現有的 Notion 帳本 + 月度分析腳本 + 加上 GitHub Pages 視覺化頁面、iOS 捷徑、自動 JSON 匯出，變成完整的家庭記帳工作流。

**Architecture:** 既有 `ledger_analysis.py` 維持不動，新增 `common/notion.py` 作為 SDK wrapper、新增 `ledger_analysis/export_json.py` 匯出靜態 JSON。GitHub Action 每月 1 號自動跑：關帳/開帳 → 匯出 JSON → commit & push。GitHub Pages 服務 `docs/` 靜態檔案，前端用 Vanilla JS + Chart.js 從 `data.json` 讀資料畫圖。iOS 捷徑直接 POST Notion API 記帳。

**Tech Stack:** Python 3.9 + notion-client SDK + pytest（後端）；Vanilla JS + Chart.js (CDN)（前端）；GitHub Actions（CI）；iOS Shortcuts（記帳）。

---

## Task 1: Project Bootstrap

建立 git repo 跟基礎開發環境。

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `common/__init__.py` (empty)

- [ ] **Step 1: git init + first commit of existing files**

```bash
cd /Users/paulwu/Documents/Github/household-budgeting
git init
git checkout -b main
git add ledger_analysis/ledger_analysis.py .github/workflows/monthly-ledger-analysis.yml docs/superpowers/
git commit -m "chore: initial commit of existing scripts and spec"
```

- [ ] **Step 2: Write `.gitignore`**

Content:
```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/

# macOS
.DS_Store

# Editor
.vscode/
.idea/

# Secrets — never commit
.env
```

- [ ] **Step 3: Write `requirements.txt`**

Content:
```
notion-client>=2.2.1
pytest>=7.0.0
```

- [ ] **Step 4: Set up Python venv and install dependencies**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Expected: successful install, no errors.

- [ ] **Step 5: Create empty `tests/__init__.py` and `common/__init__.py`**

Both files are empty (just `touch` them).

- [ ] **Step 6: Write `tests/conftest.py`** — pytest sees this; lets all tests import `common` and `ledger_analysis`

Content:
```python
import sys
from pathlib import Path

# Add project root to sys.path so `common` and `ledger_analysis` can be imported in tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 7: Run pytest to verify the test setup is in place**

Run: `pytest -v`
Expected: `no tests ran in 0.XXs` (no failures, just zero tests yet).

- [ ] **Step 8: Commit**

```bash
git add .gitignore requirements.txt tests/__init__.py tests/conftest.py common/__init__.py
git commit -m "chore: bootstrap project with venv, gitignore, pytest"
```

---

## Task 2: `common/notion.py` — `NotionApi.query_database`

第一個 wrapper 方法。TDD：mock `notion_client.Client`，驗證 wrapper 正確包裝呼叫並回傳含 `.json()` 介面的 response。

**Files:**
- Create: `common/notion.py`
- Create: `tests/test_notion.py`

- [ ] **Step 1: Write the failing test**

`tests/test_notion.py`:
```python
from unittest.mock import patch, MagicMock
from common.notion import NotionApi


def test_query_database_returns_response_with_json_method():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {"results": [{"id": "page1"}]}

        api = NotionApi(token="fake-token")
        resp = api.query_database("db-id", {"filter": {"property": "x"}})

        assert resp.status_code == 200
        assert resp.json() == {"results": [{"id": "page1"}]}
        mock_client.databases.query.assert_called_once_with(
            database_id="db-id", filter={"property": "x"}
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_notion.py::test_query_database_returns_response_with_json_method -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'common.notion'`

- [ ] **Step 3: Write minimal implementation**

`common/notion.py`:
```python
from notion_client import Client, APIResponseError


class _FakeResp:
    """讓 SDK 結果具備 ledger_analysis.py 期望的 .status_code 與 .json() 介面。"""

    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


class NotionApi:
    def __init__(self, token):
        self.client = Client(auth=token)

    def query_database(self, db_id, filter_body):
        try:
            data = self.client.databases.query(database_id=db_id, **filter_body)
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(e.status, {"error": str(e)})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_notion.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Add a test for the error path**

Append to `tests/test_notion.py`:
```python
from notion_client import APIResponseError


def test_query_database_returns_error_response_when_api_fails():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        err = APIResponseError(
            response=MagicMock(status_code=401),
            message="Unauthorized",
            code="unauthorized",
        )
        mock_client.databases.query.side_effect = err

        api = NotionApi(token="bad")
        resp = api.query_database("db-id", {})

        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["error"]
```

- [ ] **Step 6: Run tests, fix `_FakeResp` if `e.status` attr name differs**

Run: `pytest tests/test_notion.py -v`

If the test fails because `APIResponseError` has no `.status` attribute (it actually exposes `.code` and `.status`), inspect with:
```bash
python -c "from notion_client import APIResponseError; help(APIResponseError)"
```

The actual attribute is typically `e.status` (HTTP status). If not, adapt the implementation to use `getattr(e, 'status', 500)` for safety.

- [ ] **Step 7: Commit**

```bash
git add common/notion.py tests/test_notion.py
git commit -m "feat(notion): add NotionApi.query_database with error handling"
```

---

## Task 3: `common/notion.py` — `create_page` and `append_block_children`

TDD：跟 Task 2 同樣模式，加兩個方法。

**Files:**
- Modify: `common/notion.py`
- Modify: `tests/test_notion.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_notion.py`:
```python
def test_create_page_calls_pages_create():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "new-page-id"}

        api = NotionApi(token="t")
        properties = {"Name": {"title": [{"text": {"content": "test"}}]}}
        resp = api.create_page("db-id", properties)

        assert resp.status_code == 200
        assert resp.json()["id"] == "new-page-id"
        mock_client.pages.create.assert_called_once_with(
            parent={"database_id": "db-id"}, properties=properties
        )


def test_append_block_children_calls_blocks_children_append():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.blocks.children.append.return_value = {"results": []}

        api = NotionApi(token="t")
        blocks = [{"type": "paragraph"}]
        resp = api.append_block_children("page-id", blocks)

        assert resp.status_code == 200
        mock_client.blocks.children.append.assert_called_once_with(
            block_id="page-id", children=blocks
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notion.py -v`
Expected: 2 new tests FAIL with `AttributeError: 'NotionApi' object has no attribute 'create_page'` (and similar for append).

- [ ] **Step 3: Implement both methods**

Append to `common/notion.py` inside `NotionApi`:
```python
    def create_page(self, db_id, properties):
        try:
            data = self.client.pages.create(
                parent={"database_id": db_id}, properties=properties
            )
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})

    def append_block_children(self, page_id, blocks):
        try:
            data = self.client.blocks.children.append(
                block_id=page_id, children=blocks
            )
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest tests/test_notion.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add common/notion.py tests/test_notion.py
git commit -m "feat(notion): add create_page and append_block_children"
```

---

## Task 4: `common/notion.py` — `get_property_names_by_type` and `check_record_exists`

`ledger_analysis.py` 用到的兩個 helper。

**Files:**
- Modify: `common/notion.py`
- Modify: `tests/test_notion.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_notion.py`:
```python
def test_get_property_names_by_type_filters_properties():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "名目": {"type": "title"},
                "備註": {"type": "rich_text"},
                "Paul": {"type": "number"},
            }
        }

        api = NotionApi(token="t")
        result = api.get_property_names_by_type("db-id", ["title", "rich_text"])

        assert result == {"title": "名目", "rich_text": "備註"}


def test_check_record_exists_returns_true_when_results_nonempty():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {
            "results": [{"id": "found"}]
        }

        api = NotionApi(token="t")
        exists = api.check_record_exists("db-id", "名目", "202504")

        assert exists is True
        mock_client.databases.query.assert_called_once_with(
            database_id="db-id",
            filter={"property": "名目", "title": {"equals": "202504"}},
        )


def test_check_record_exists_returns_false_when_results_empty():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {"results": []}

        api = NotionApi(token="t")
        assert api.check_record_exists("db-id", "名目", "notfound") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notion.py -v`
Expected: 3 new tests FAIL.

- [ ] **Step 3: Implement both methods**

Append to `common/notion.py` inside `NotionApi`:
```python
    def get_property_names_by_type(self, db_id, types):
        db = self.client.databases.retrieve(database_id=db_id)
        out = {}
        for name, prop in db["properties"].items():
            if prop["type"] in types and prop["type"] not in out:
                out[prop["type"]] = name
        return out

    def check_record_exists(self, db_id, title_prop_name, value):
        resp = self.client.databases.query(
            database_id=db_id,
            filter={"property": title_prop_name, "title": {"equals": value}},
        )
        return len(resp["results"]) > 0
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `pytest tests/test_notion.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add common/notion.py tests/test_notion.py
git commit -m "feat(notion): add get_property_names_by_type and check_record_exists"
```

---

## Task 5: 驗證 ledger_analysis.py 的 formula filter

Spec 開放問題 2：Notion API 對 formula 欄位的 filter 語法可能跟現有腳本不一致。寫一個簡單的 verify script 用實際 token 驗證。如果 filter 不對，修正 `ledger_analysis.py` 並寫測試。

**Files:**
- Create: `scripts/verify_formula_filter.py` (manual smoke test, not part of CI)
- Possibly modify: `ledger_analysis/ledger_analysis.py`

- [ ] **Step 1: Write a one-off verify script**

Create `scripts/verify_formula_filter.py`:
```python
"""Manual smoke test: verify that Notion API accepts the existing filter for
the formula-typed `時間` property. Run locally with NOTION_SECRET set."""
import os
import datetime
from notion_client import Client

client = Client(auth=os.environ["NOTION_SECRET"])
DB_ID = "43c59e00321e49a69d85037f0f45ba7e"

# Use a recent fixed range (last 30 days) to ensure some rows exist
now = datetime.datetime.now(datetime.timezone.utc)
after = (now - datetime.timedelta(days=30)).isoformat()
before = now.isoformat()

# Variant A: existing script syntax (might be invalid for formula property)
print("=== Variant A: bare date filter ===")
try:
    resp = client.databases.query(
        database_id=DB_ID,
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
    resp = client.databases.query(
        database_id=DB_ID,
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
```

- [ ] **Step 2: Run the verify script with real Notion token**

Run:
```bash
source .venv/bin/activate
python scripts/verify_formula_filter.py
```

Inspect output. Three possible outcomes:
1. Both variants work and return data → existing filter is fine, no change needed.
2. Only Variant B works → existing filter has a bug; need to fix `ledger_analysis.py` and use B in `export_json.py`.
3. Both fail → something else is wrong; debug before continuing.

- [ ] **Step 3a (only if Variant A fails): Fix `ledger_analysis/ledger_analysis.py`**

Modify lines 41–106 (the two `filter_body_*` dicts) — wrap each `"date": {...}` with `"formula": {"date": {...}}`:

Before:
```python
{"property": "時間", "date": {"after": start_datetime.isoformat()}},
```
After:
```python
{"property": "時間", "formula": {"date": {"after": start_datetime.isoformat()}}},
```

Apply to all 4 occurrences (2 in `filter_body_chart`, 2 in `filter_body_all`).

- [ ] **Step 3b (only if changes made): Commit fix**

```bash
git add ledger_analysis/ledger_analysis.py
git commit -m "fix(ledger_analysis): use formula.date filter for 時間 property"
```

- [ ] **Step 4: Record the verified filter syntax for use in export_json.py**

In `scripts/verify_formula_filter.py` (or just remember from output), note which variant works. The rest of the plan assumes Variant B (`formula.date`) is correct; if Variant A turns out to be correct, swap that pattern wherever the plan shows `formula.date`.

- [ ] **Step 5: Commit verify script (kept in repo as documentation of the check)**

```bash
git add scripts/verify_formula_filter.py
git commit -m "chore: add manual verify script for formula filter"
```

---

## Task 6: `export_json.py` — Core aggregation logic (unit-testable)

把「給定 Notion query results → 算出該月 by_category / by_funds / total」這段純邏輯抽成 pure function，獨立測試。

**Files:**
- Create: `ledger_analysis/export_json.py`
- Create: `tests/test_export_json.py`

- [ ] **Step 1: Write the failing test**

`tests/test_export_json.py`:
```python
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
        _row("收入", paul=10000),  # should be filtered out
        _row("財務整理", paul=-99999),  # should be filtered out
    ]

    result = aggregate_month(rows)

    assert result["by_category"] == {"飲食": 500}
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_json.py -v`
Expected: `ModuleNotFoundError: No module named 'ledger_analysis.export_json'`

- [ ] **Step 3: Create `ledger_analysis/__init__.py` if it doesn't exist**

Run:
```bash
ls ledger_analysis/__init__.py 2>/dev/null || touch ledger_analysis/__init__.py
```

- [ ] **Step 4: Implement `aggregate_month`**

Create `ledger_analysis/export_json.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_export_json.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add ledger_analysis/export_json.py ledger_analysis/__init__.py tests/test_export_json.py
git commit -m "feat(export_json): add aggregate_month pure function with tests"
```

---

## Task 7: `export_json.py` — File I/O (read/write data.json with idempotent merge)

`load_existing_data` 讀取舊 `data.json`（不存在時回傳空骨架），`merge_month` 將新月份合併到 `months` 物件。

**Files:**
- Modify: `ledger_analysis/export_json.py`
- Modify: `tests/test_export_json.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_export_json.py`:
```python
import json
from pathlib import Path
from ledger_analysis.export_json import load_existing_data, merge_month, save_data


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_export_json.py -v`
Expected: 4 new tests FAIL with `ImportError`.

- [ ] **Step 3: Implement functions**

Append to `ledger_analysis/export_json.py`:
```python
import json
from pathlib import Path


def load_existing_data(path):
    """Read existing data.json or return empty skeleton if file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return {
            "generated_at": None,
            "categories": list(TARGET_CATEGORIES),
            "members": ["Paul", "Lily"],
            "months": {},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def merge_month(data, yyyymm, month_agg):
    """Insert or overwrite the given month's aggregate in data['months']."""
    data["months"][yyyymm] = month_agg


def save_data(path, data):
    """Write data as pretty-printed JSON (ensure_ascii=False for Chinese)."""
    path = Path(path)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_export_json.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add ledger_analysis/export_json.py tests/test_export_json.py
git commit -m "feat(export_json): add load/merge/save functions for data.json"
```

---

## Task 8: `export_json.py` — Main entry point (integration)

整合：算上月日期區間、query Notion、aggregate、merge、save。

**Files:**
- Modify: `ledger_analysis/export_json.py`
- Modify: `tests/test_export_json.py`

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_export_json.py`:
```python
from unittest.mock import patch, MagicMock
import datetime


def test_main_queries_last_month_aggregates_and_writes_json(tmp_path, monkeypatch):
    # Fix "today" to 2025-05-15 → last month is 2025-04
    fake_today = datetime.date(2025, 5, 15)

    class FakeDate(datetime.date):
        @classmethod
        def today(cls):
            return fake_today

    monkeypatch.setattr("ledger_analysis.export_json.datetime", datetime)
    monkeypatch.setattr("ledger_analysis.export_json.date", FakeDate)
    monkeypatch.setenv("NOTION_SECRET", "fake-token")

    fake_rows = [
        {"properties": {
            "分類": {"select": {"name": "飲食"}},
            "Paul": {"number": -1000},
            "Lily": {"number": None},
            "現金": {"number": None},
            "銀行存款": {"number": None},
        }}
    ]

    output_path = tmp_path / "data.json"

    with patch("ledger_analysis.export_json.NotionApi") as MockApi:
        mock_api = MagicMock()
        MockApi.return_value = mock_api
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": fake_rows}
        mock_api.query_database.return_value = mock_resp

        from ledger_analysis.export_json import main
        main(output_path)

    import json
    result = json.loads(output_path.read_text())
    assert "202504" in result["months"]
    assert result["months"]["202504"]["by_category"]["飲食"] == 1000
    assert result["months"]["202504"]["by_funds"]["Paul"] == 1000
    assert result["generated_at"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_json.py::test_main_queries_last_month_aggregates_and_writes_json -v`
Expected: FAIL with `ImportError` or `AttributeError: main`

- [ ] **Step 3: Implement `main`**

Append to `ledger_analysis/export_json.py`:
```python
import os
import calendar
from datetime import date, datetime, time, timedelta, timezone
from common.notion import NotionApi

LEDGER_DB_ID = "43c59e00321e49a69d85037f0f45ba7e"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "data.json"


def _last_month_range(today):
    """Return (start_iso, end_iso, yyyymm) for the month before `today`."""
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    start = datetime.combine(first, time.min) - timedelta(seconds=1)
    end = datetime.combine(last, time.max)
    return start.isoformat(), end.isoformat(), f"{year}{month:02d}"


def _build_filter(start_iso, end_iso):
    """Build the Notion query filter for the target categories within [start, end]."""
    # NOTE: if Task 5 determined the bare `date` syntax works for the formula property,
    # swap "formula": {"date": ...} for "date": ...  here.
    return {
        "filter": {
            "and": [
                {"property": "時間", "formula": {"date": {"after": start_iso}}},
                {"property": "時間", "formula": {"date": {"before": end_iso}}},
                {
                    "or": [
                        {"property": "分類", "select": {"equals": c}}
                        for c in TARGET_CATEGORIES
                    ]
                },
            ]
        }
    }


def main(output_path=DEFAULT_OUTPUT):
    token = os.environ["NOTION_SECRET"]
    api = NotionApi(token)

    start_iso, end_iso, yyyymm = _last_month_range(date.today())
    resp = api.query_database(LEDGER_DB_ID, _build_filter(start_iso, end_iso))
    rows = resp.json()["results"]

    month_agg = aggregate_month(rows)
    data = load_existing_data(output_path)
    merge_month(data, yyyymm, month_agg)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    save_data(output_path, data)
    print(f"Exported {yyyymm}: total={month_agg['total']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_export_json.py -v`
Expected: 9 passed

(If the `monkeypatch` of `date.today()` doesn't work the way the test expects — pytest sometimes needs a slightly different approach — adjust by patching `ledger_analysis.export_json.date` to a custom class as shown, and `main` reads `date.today()`. The test code already does this.)

- [ ] **Step 5: Smoke test with real Notion token (manual)**

Run:
```bash
source .venv/bin/activate
export NOTION_SECRET="<your real token>"
python ledger_analysis/export_json.py
```

Expected: `docs/data.json` is created/updated, `print` shows the previous month total.

Inspect the file:
```bash
cat docs/data.json | python -m json.tool
```

Expected: valid JSON with structure matching the spec.

- [ ] **Step 6: Commit**

```bash
git add ledger_analysis/export_json.py tests/test_export_json.py docs/data.json
git commit -m "feat(export_json): add main entry point and generate initial data.json"
```

---

## Task 9: Update GitHub Action workflow

加入 `export_json` step、commit & push step、`permissions: contents: write`。

**Files:**
- Modify: `.github/workflows/monthly-ledger-analysis.yml`

- [ ] **Step 1: Replace the workflow file**

Overwrite `.github/workflows/monthly-ledger-analysis.yml`:
```yaml
name: Monthly Ledger Analysis

on:
  schedule:
    # 每月 1 號 UTC 00:00 (台灣早上 08:00)
    - cron: '0 0 1 * *'
  workflow_dispatch:  # 允許手動觸發

permissions:
  contents: write  # 需要 push commit 回 main

jobs:
  ledger-analysis:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run monthly close + mermaid analysis
        env:
          NOTION_SECRET: ${{ secrets.NOTION_SECRET }}
        run: python ledger_analysis/ledger_analysis.py

      - name: Export JSON for GitHub Pages
        env:
          NOTION_SECRET: ${{ secrets.NOTION_SECRET }}
        run: python ledger_analysis/export_json.py

      - name: Commit updated data.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data.json
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "chore: update data.json for $(date +%Y-%m)"
            git push
          fi
```

- [ ] **Step 2: Verify YAML syntax**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/monthly-ledger-analysis.yml'))"
```
Expected: no output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/monthly-ledger-analysis.yml
git commit -m "ci: add export_json step and auto-commit data.json"
```

---

## Task 10: `docs/index.html` — HTML skeleton

純 markup + 基礎 CSS。沒 TDD（無邏輯）。

**Files:**
- Create: `docs/index.html`

- [ ] **Step 1: Write the HTML file**

Create `docs/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>家庭記帳分析</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "PingFang TC", "Microsoft JhengHei", sans-serif;
      max-width: 1100px;
      margin: 0 auto;
      padding: 1rem;
      background: #fafafa;
      color: #222;
    }
    header h1 { margin-bottom: 0.5rem; }
    nav.tabs { display: flex; gap: 0.5rem; margin: 1rem 0; }
    nav.tabs button {
      padding: 0.5rem 1rem;
      border: 1px solid #ccc;
      background: white;
      cursor: pointer;
      border-radius: 6px;
    }
    nav.tabs button.active { background: #2c5aa0; color: white; border-color: #2c5aa0; }
    .picker { margin-bottom: 1.5rem; }
    .picker select { padding: 0.4rem; font-size: 1rem; }
    main {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .chart-line { grid-column: 1 / -1; }
    section {
      background: white;
      border-radius: 8px;
      padding: 1rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    canvas { max-height: 360px; }
    #status { color: #888; font-size: 0.9rem; }
  </style>
</head>
<body>
  <header>
    <h1>家庭記帳分析</h1>
    <p id="status">載入中…</p>
  </header>

  <nav class="tabs">
    <button data-view="month" class="active">月視圖</button>
    <button data-view="year">年視圖</button>
  </nav>

  <div class="picker">
    期間：<select id="period-select"></select>
  </div>

  <main>
    <section class="chart-pie"><canvas id="pie"></canvas></section>
    <section class="chart-bar"><canvas id="bar"></canvas></section>
    <section class="chart-line"><canvas id="line"></canvas></section>
  </main>

  <script src="main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add docs/index.html
git commit -m "feat(docs): add HTML skeleton with Chart.js and grid layout"
```

---

## Task 11: `docs/main.js` — Data loading + utility helpers

`loadData`, `getMonths`, `getYears`, color palette.

**Files:**
- Create: `docs/main.js`

- [ ] **Step 1: Write the helpers**

Create `docs/main.js`:
```javascript
// ---- Color palette (synced with ledger_analysis.py mermaid colors) ----
const CATEGORY_COLORS = {
  娛樂: "#FF0000",
  日常用品: "#FFFF00",
  飲食: "#00FF00",
  水電管理費: "#0000FF",
};
const FUND_COLORS = {
  Paul: "#4E79A7",
  Lily: "#F28E2B",
  現金: "#59A14F",
  銀行存款: "#76B7B2",
};

// ---- State ----
let chartInstances = { pie: null, bar: null, line: null };

// ---- Data loading ----
async function loadData() {
  const resp = await fetch("./data.json", { cache: "no-store" });
  if (!resp.ok) throw new Error(`Failed to load data.json: ${resp.status}`);
  return await resp.json();
}

function getMonths(data) {
  return Object.keys(data.months).sort().reverse(); // newest first
}

function getYears(data) {
  const years = new Set();
  for (const yyyymm of Object.keys(data.months)) {
    years.add(yyyymm.slice(0, 4));
  }
  return [...years].sort().reverse();
}

function destroyCharts() {
  for (const k of Object.keys(chartInstances)) {
    if (chartInstances[k]) {
      chartInstances[k].destroy();
      chartInstances[k] = null;
    }
  }
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}
```

- [ ] **Step 2: Manual smoke test in a temp browser**

Generate a minimal data.json if you don't have one yet (paste into `docs/data.json` for local testing):
```json
{
  "generated_at": "2025-05-01T00:00:00+08:00",
  "categories": ["娛樂", "飲食", "日常用品", "水電管理費"],
  "members": ["Paul", "Lily"],
  "months": {
    "202504": {
      "by_category": {"娛樂": 1200, "飲食": 8500, "日常用品": 2300, "水電管理費": 3000},
      "by_funds": {"Paul": 4000, "Lily": 3000, "現金": 2000, "銀行存款": 6000},
      "total": 15000
    }
  }
}
```

Run a quick local server:
```bash
cd docs && python3 -m http.server 8000
```

Open http://localhost:8000 in browser. Open DevTools console. Status should still say "載入中…" because we haven't wired up render yet. There should be no JS errors and `await loadData()` typed into the console should return the parsed object.

- [ ] **Step 3: Commit**

```bash
git add docs/main.js
git commit -m "feat(docs): add data loading and color palette helpers"
```

---

## Task 12: `docs/main.js` — Render monthly view (3 charts)

**Files:**
- Modify: `docs/main.js`

- [ ] **Step 1: Append monthly rendering functions**

Append to `docs/main.js`:
```javascript
// ---- Monthly view ----
function renderMonthlyView(data, yyyymm) {
  destroyCharts();
  const month = data.months[yyyymm];
  if (!month) {
    setStatus(`${yyyymm} 沒有資料`);
    return;
  }
  setStatus(`月視圖：${yyyymm}（總額 ${month.total.toLocaleString()}）`);

  // --- Pie: by_category ---
  const cats = data.categories;
  chartInstances.pie = new Chart(document.getElementById("pie"), {
    type: "pie",
    data: {
      labels: cats,
      datasets: [{
        data: cats.map(c => month.by_category[c] || 0),
        backgroundColor: cats.map(c => CATEGORY_COLORS[c]),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyymm} 分類佔比` } },
    },
  });

  // --- Bar: by_funds (4 bars) ---
  const funds = Object.keys(month.by_funds);
  chartInstances.bar = new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
      labels: funds,
      datasets: [{
        label: "支出",
        data: funds.map(f => month.by_funds[f] || 0),
        backgroundColor: funds.map(f => FUND_COLORS[f] || "#999"),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyymm} 資金來源支出` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // --- Line: past 6 months category trend ---
  const allMonths = Object.keys(data.months).sort();
  const idx = allMonths.indexOf(yyyymm);
  const window = allMonths.slice(Math.max(0, idx - 5), idx + 1); // up to 6 months ending at yyyymm
  chartInstances.line = new Chart(document.getElementById("line"), {
    type: "line",
    data: {
      labels: window,
      datasets: cats.map(c => ({
        label: c,
        data: window.map(m => (data.months[m].by_category[c] || 0)),
        borderColor: CATEGORY_COLORS[c],
        backgroundColor: CATEGORY_COLORS[c],
        tension: 0.2,
      })),
    },
    options: {
      plugins: { title: { display: true, text: `近 ${window.length} 個月分類趨勢` } },
      scales: { y: { beginAtZero: true } },
    },
  });
}
```

- [ ] **Step 2: Manual browser smoke test**

In DevTools console (after the page loads):
```javascript
const data = await loadData();
renderMonthlyView(data, "202504");
```

Expected: three charts render, pie shows category proportions, bar shows 4 funds, line shows the single month.

- [ ] **Step 3: Commit**

```bash
git add docs/main.js
git commit -m "feat(docs): render monthly view with pie/bar/line charts"
```

---

## Task 13: `docs/main.js` — Render yearly view

**Files:**
- Modify: `docs/main.js`

- [ ] **Step 1: Append yearly rendering function**

Append to `docs/main.js`:
```javascript
// ---- Yearly view ----
function renderYearlyView(data, yyyy) {
  destroyCharts();
  // Collect all months belonging to that year
  const monthsInYear = Object.keys(data.months)
    .filter(m => m.startsWith(yyyy))
    .sort();
  if (monthsInYear.length === 0) {
    setStatus(`${yyyy} 沒有資料`);
    return;
  }

  // Aggregate by_category for the year
  const cats = data.categories;
  const yearCat = Object.fromEntries(cats.map(c => [c, 0]));
  let yearTotal = 0;
  for (const m of monthsInYear) {
    for (const c of cats) {
      yearCat[c] += data.months[m].by_category[c] || 0;
    }
    yearTotal += data.months[m].total || 0;
  }
  setStatus(`年視圖：${yyyy}（總額 ${yearTotal.toLocaleString()}）`);

  // --- Pie: yearly by_category ---
  chartInstances.pie = new Chart(document.getElementById("pie"), {
    type: "pie",
    data: {
      labels: cats,
      datasets: [{
        data: cats.map(c => yearCat[c]),
        backgroundColor: cats.map(c => CATEGORY_COLORS[c]),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 年度分類佔比` } },
    },
  });

  // --- Bar: 12 months total ---
  const months12 = Array.from({ length: 12 }, (_, i) => `${yyyy}${String(i+1).padStart(2,"0")}`);
  const monthTotals = months12.map(m => (data.months[m] ? data.months[m].total : 0));
  chartInstances.bar = new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
      labels: months12.map(m => m.slice(4)), // "01"..."12"
      datasets: [{
        label: "每月總支出",
        data: monthTotals,
        backgroundColor: "#2c5aa0",
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 每月總支出` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // --- Line: cumulative total ---
  let running = 0;
  const cumulative = monthTotals.map(v => (running += v));
  chartInstances.line = new Chart(document.getElementById("line"), {
    type: "line",
    data: {
      labels: months12.map(m => m.slice(4)),
      datasets: [{
        label: "累計支出",
        data: cumulative,
        borderColor: "#c0392b",
        backgroundColor: "#c0392b",
        tension: 0.2,
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 累計支出趨勢` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}
```

- [ ] **Step 2: Manual smoke test**

In browser console:
```javascript
const data = await loadData();
renderYearlyView(data, "2025");
```

Expected: pie (year aggregate), bar (12 bars for 1-12 月), line (monotonically rising cumulative).

- [ ] **Step 3: Commit**

```bash
git add docs/main.js
git commit -m "feat(docs): render yearly view with year-aggregate pie, monthly bars, cumulative line"
```

---

## Task 14: `docs/main.js` — Wire up tabs and dropdown

**Files:**
- Modify: `docs/main.js`

- [ ] **Step 1: Append UI controller**

Append to `docs/main.js`:
```javascript
// ---- UI controller ----
function setupUI(data) {
  const select = document.getElementById("period-select");
  const tabs = document.querySelectorAll("nav.tabs button");
  let currentView = "month";

  function populateSelect() {
    const periods = currentView === "month" ? getMonths(data) : getYears(data);
    select.innerHTML = periods.map(p => `<option value="${p}">${p}</option>`).join("");
  }

  function render() {
    const period = select.value;
    if (!period) return;
    if (currentView === "month") {
      renderMonthlyView(data, period);
    } else {
      renderYearlyView(data, period);
    }
  }

  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentView = btn.dataset.view;
      populateSelect();
      render();
    });
  });

  select.addEventListener("change", render);

  populateSelect();
  render();
}

// ---- Bootstrap ----
(async () => {
  try {
    const data = await loadData();
    setupUI(data);
  } catch (err) {
    console.error(err);
    setStatus(`載入失敗：${err.message}`);
  }
})();
```

- [ ] **Step 2: Full end-to-end manual smoke test**

```bash
cd docs && python3 -m http.server 8000
```

Open http://localhost:8000. Verify:
- Page loads, status shows current month
- Three charts render with the test data
- Click "年視圖" tab — dropdown changes to years, three charts re-render
- Click "月視圖" tab — dropdown back to months
- Change dropdown selection — charts re-render
- No console errors

If charts don't render or there are errors, inspect console and fix before committing.

- [ ] **Step 3: Commit**

```bash
git add docs/main.js
git commit -m "feat(docs): wire up tabs and period dropdown"
```

---

## Task 15: `shortcuts/shortcut-template.md` — iOS shortcut spec

純文件，無 TDD。

**Files:**
- Create: `shortcuts/shortcut-template.md`

- [ ] **Step 1: Write the file**

Create `shortcuts/shortcut-template.md`:
```markdown
# iOS 捷徑：快速記帳

在 iPhone Shortcuts App 內手動建立一個叫「快速記帳」的捷徑，按下面步驟設定。

## 動作流程

| # | Shortcuts 動作 | 設定 |
|---|---|---|
| 1 | Choose from List | 清單：娛樂 / 飲食 / 日常用品 / 水電管理費 / 房屋相關 / 收入 / 其它 → 變數 `category` |
| 2 | Ask for Input | Input Type: Number；提示：「金額（正數）？」→ 變數 `amount` |
| 3 | Choose from List | 清單：Paul / Lily / 現金 / 銀行存款 → 變數 `payer` |
| 4 | Ask for Input | Input Type: Text；提示：「名目（例如店家名）？」→ 變數 `note` |
| 5 | If | 條件：`category` is 收入 |
| 5a |   Set Variable | `signed_amount` = `amount` |
| 5b | Otherwise | |
| 5c |   Calculate | `signed_amount` = `amount × -1` |
| 5d | End If | |
| 6 | Get Contents of URL | URL: `https://api.notion.com/v1/pages`<br>Method: POST<br>Headers / Body 見下方 |
| 7 | Show Result | 顯示 API 回應狀態 |

## Get Contents of URL 設定

**URL**：`https://api.notion.com/v1/pages`

**Method**：POST

**Headers**：
```
Authorization: Bearer <你的 NOTION_SECRET>
Notion-Version: 2022-06-28
Content-Type: application/json
```

**Request Body**（JSON，把 `<category>` `<note>` `<payer>` `<signed_amount>` 換成捷徑變數）：
```json
{
  "parent": { "database_id": "43c59e00321e49a69d85037f0f45ba7e" },
  "properties": {
    "名目": { "title": [{ "text": { "content": "<note>" } }] },
    "分類": { "select": { "name": "<category>" } },
    "<payer>": { "number": <signed_amount> }
  }
}
```

注意 `<payer>` 是動態的 key（值為 `Paul` / `Lily` / `現金` / `銀行存款` 之一）。
Shortcuts 對動態 key 的處理方式是用 "Dictionary" 動作建構 JSON 物件，
或者用 "Replace Text" 在預先寫好的 JSON 字串裡替換 placeholder。

## 為什麼不放 `.shortcut` 二進位檔到 repo

`.shortcut` 是 Apple plist 格式，AI 無法生成可用版本，且日後修改不易維護。
照本文件規格手動建一次即可。建議建好後在 iCloud 備份（Shortcuts → 三點選單 → Share → Copy iCloud Link）。

## 安全提醒

- Token 寫在捷徑內等於把帳本寫權限放在你的 iPhone 上，請勿分享捷徑檔給他人
- 若要重設 token，到 Notion → My integrations 重新產生

## 測試

建好後執行一次：
1. 選「飲食」
2. 輸入 `100`
3. 選「現金」
4. 輸入「測試」
5. 完成後到 Notion「共用帳本」DB 找到一筆「名目=測試、分類=飲食、現金=-100」的紀錄
6. 確認後刪掉這筆測試資料
```

- [ ] **Step 2: Commit**

```bash
git add shortcuts/shortcut-template.md
git commit -m "docs(shortcuts): add iOS shortcut spec"
```

---

## Task 16: `README.md` — Personal version

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Create `README.md`:
```markdown
# 家庭記帳

家庭記帳工作流，由三部分組成：

## 1. Notion 帳本

- 共用帳本 DB：`43c59e00321e49a69d85037f0f45ba7e`
- 每月分析 DB：`25c8303f78f780fd9227e5e9d54c6b43`
- 欄位：`名目`（title）、`分類`（select）、`Paul` / `Lily` / `現金` / `銀行存款`（number）、`備註`（rich_text）、`時間`（formula）、`修正時間`（date）
- 慣例：支出記負、收入記正，每筆只填一個 number 欄位（Paul / Lily / 現金 / 銀行存款 擇一）

## 2. 自動月結（GitHub Action）

每月 1 號 UTC 0:00（台灣早上 8:00）自動執行 `.github/workflows/monthly-ledger-analysis.yml`，做：
1. 跑 `ledger_analysis/ledger_analysis.py`：算上月 4 大分類加總，產 mermaid 圖寫進「每月分析」DB；建立關帳、開帳記錄
2. 跑 `ledger_analysis/export_json.py`：把上月分類/資金來源加總寫進 `docs/data.json`
3. 把 `docs/data.json` commit 回 main 並 push

## 3. 視覺化頁面（GitHub Pages）

URL：（Pages 啟用後填入，例如 `https://easylive1989.github.io/household-budgeting/`）

- 月視圖：圓餅(分類佔比) / 長條(資金來源支出) / 折線(過去 6 個月分類趨勢)
- 年視圖：圓餅(年度分類佔比) / 長條(12 個月總支出) / 折線(累計支出趨勢)

## 4. iOS 捷徑

照 `shortcuts/shortcut-template.md` 在 iPhone Shortcuts App 手動建立。

## 初次設定

1. Repo Settings → Secrets and variables → Actions → New repository secret
   - Name: `NOTION_SECRET`
   - Value: 從 Notion → My integrations 取得的 token
2. Repo Settings → Pages → Source: Deploy from a branch → Branch: `main`, folder: `/docs`
3. 在 iPhone 照 `shortcuts/shortcut-template.md` 建立捷徑
4. 本地測試（可選）：
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   export NOTION_SECRET="<your-token>"
   python ledger_analysis/export_json.py    # 產 docs/data.json
   cd docs && python3 -m http.server 8000   # 本地預覽
   ```

## 開發

```bash
source .venv/bin/activate
pytest -v     # 跑單元測試
```

## 目錄結構

```
.
├── .github/workflows/monthly-ledger-analysis.yml
├── common/notion.py            # Notion SDK wrapper
├── ledger_analysis/
│   ├── ledger_analysis.py      # 月結 + mermaid 圖
│   └── export_json.py          # 匯出 docs/data.json
├── docs/                       # GitHub Pages 根目錄
│   ├── index.html
│   ├── main.js
│   └── data.json
├── shortcuts/
│   └── shortcut-template.md
└── tests/
    ├── test_notion.py
    └── test_export_json.py
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add personal-version README"
```

---

## Task 17: Final integration — push to GitHub, enable Pages, end-to-end verify

**Files:**
- (none new)

- [ ] **Step 1: Add remote and push**

Run:
```bash
git remote add origin https://github.com/easylive1989/household-budgeting.git
git branch -M main
git push -u origin main
```

If the remote already has unrelated history, this push will fail. In that case, stop and decide with the user whether to force-push or merge.

- [ ] **Step 2: Set `NOTION_SECRET` repo secret**

On GitHub: Settings → Secrets and variables → Actions → New repository secret
- Name: `NOTION_SECRET`
- Value: your Notion integration token

- [ ] **Step 3: Enable GitHub Pages**

On GitHub: Settings → Pages
- Source: Deploy from a branch
- Branch: `main`, folder: `/docs`
- Save

Wait ~1 min, the URL will be displayed (e.g. `https://easylive1989.github.io/household-budgeting/`).

- [ ] **Step 4: Manually trigger the workflow**

On GitHub: Actions → "Monthly Ledger Analysis" → Run workflow → from `main`

Watch the run log. Expected:
- `ledger_analysis.py` step succeeds (might create關帳/開帳 records and a mermaid page if not yet present)
- `export_json.py` step succeeds, prints "Exported YYYYMM: total=..."
- Commit step pushes a new commit if `data.json` changed (or "No changes to commit" if same)

- [ ] **Step 5: Verify GitHub Pages site shows data**

Open the Pages URL. Verify:
- Page loads, status line shows the latest month
- Three charts render with correct data
- Tab switching + dropdown work

If charts don't show data, inspect Network tab — `data.json` should return 200 with the expected content. If 404, Pages cache may not be ready yet (wait a few minutes).

- [ ] **Step 6: Test iOS shortcut**

On iPhone, run the "快速記帳" shortcut. Enter a test record. Verify in Notion that a new row appears with correct fields.

After verification, delete the test row in Notion.

- [ ] **Step 7: Final commit (if any README updates needed)**

If you discovered any setup discrepancies during integration (URL, paths, etc.), update README:
```bash
git add README.md
git commit -m "docs: fix README based on real Pages URL"
git push
```

---

## Plan Self-Review

**Spec coverage check:**
- ✅ Section 1 (JSON schema): Task 6 + Task 7 implement aggregation and persistence; Task 8 wires the main entry
- ✅ Section 2 (Frontend): Tasks 10–14 cover HTML, helpers, monthly view, yearly view, UI
- ✅ Section 3 (Action workflow): Task 9
- ✅ Section 4 (iOS shortcut): Task 15
- ✅ Section 5 (common/notion.py): Tasks 2–4 (each method TDD'd individually)
- ✅ Section 6 (README): Task 16
- ✅ Section 7 (requirements.txt): Task 1
- ✅ Testing strategy: pytest tests in Tasks 2, 3, 4, 6, 7, 8; manual smoke in Tasks 11, 12, 13, 14, 17
- ✅ Open question 1 (long-tail bar funds maintains data alignment): implemented as `by_funds` in Task 6
- ✅ Open question 2 (formula filter validation): Task 5 verifies and fixes if needed

**Placeholder scan:** All steps contain concrete code or commands. The only "fill in" is the final Pages URL in README (Task 16/17), which can't be known until Pages is enabled.

**Type consistency check:**
- `aggregate_month` returns `{by_category, by_funds, total}` — used identically in Task 7 (`merge_month`), Task 8 (`main`), and frontend reads same keys
- `NotionApi` methods: `query_database`, `create_page`, `append_block_children`, `get_property_names_by_type`, `check_record_exists` — names consistent throughout
- JSON shape: `data.months[YYYYMM].by_category` / `.by_funds` / `.total` — consistent in Task 6, 7, 8, 11, 12, 13

No issues found.
