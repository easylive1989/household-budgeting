# 每月統計寫進 Google Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每月月結後，把 Notion「分析」DB 的所有月份寫進「消費分析」試算表的「家庭月統計」分頁，並移除 GitHub Pages 網頁。

**Architecture:** 把 `export_json.py` 改名為 `export_sheet.py`：沿用讀 Notion 的部分，改成組 rows 後用 `urllib` POST 給 Apps Script Web App。Web App 以使用者本人身分執行，驗證 token 後全量覆寫「家庭月統計」分頁。GitHub Action 移除 Pages 部署步驟。

**Tech Stack:** Python 3.13（標準庫 `urllib`、`json`）、pytest、Google Apps Script、GitHub Actions

**Spec:** `docs/superpowers/specs/2026-11-17-google-sheet-export-design.md`

## Global Constraints

- 不新增 Python 依賴（`requirements.txt` 不動）
- 分頁名稱：`家庭月統計`
- Header 固定為：`["月份", "娛樂", "飲食", "日常用品", "水電管理費", "Paul", "Lily", "現金", "銀行存款", "總額"]`
- 環境變數 / GitHub secrets：`NOTION_SECRET`（既有）、`SHEET_WEBAPP_URL`、`SHEET_TOKEN`
- Apps Script 的 Script Properties key：`SHEET_TOKEN`
- Web App 回應格式：成功時是 `{"ok": true, "rows": <n>}`，失敗時是 `{"ok": false, "error": "<msg>"}`
- Apps Script 只能讀寫「家庭月統計」分頁，其他分頁完全不碰
- 數值照 Notion「分析」DB 的值原樣寫入
- `ledger_analysis/ledger_analysis.py` 不動

## Review Focus

- Web App 回傳的是 HTML（例如部署權限設錯，回到 Google 登入頁）而不是 JSON → `post_rows` 要拋出含回應片段的錯誤，Action 要失敗，不能當成功（Task 2 有測試）
- 回 `{"ok": false}`（token 錯誤）→ Action 必須失敗（Task 2 有測試）
- Notion 讀不到任何月份（0 筆）→ 不 POST，以錯誤結束，避免把試算表清空（Task 2 有測試）
- 月份順序：Notion 回傳的順序不固定 → rows 必須依 `YYYYMM` 升冪排列（Task 1 有測試）
- 環境變數缺少 `SHEET_WEBAPP_URL` 或 `SHEET_TOKEN` → 開頭就以清楚的 KeyError 結束，不要先讀 Notion（Task 2 有測試）

---

### Task 1: 把 export_json 改名為 export_sheet，加上 `build_rows`

**Files:**
- Rename: `ledger_analysis/export_json.py` → `ledger_analysis/export_sheet.py`（`git mv`）
- Rename: `tests/test_export_json.py` → `tests/test_export_sheet.py`（`git mv`）
- Modify: `ledger_analysis/export_sheet.py`：刪除 `save_data`、`DEFAULT_OUTPUT`、舊的 `main`（Task 2 會重寫）。保留 `fetch_all_pages`、`page_to_month_entry`、`CATEGORIES`、`FUND_FIELDS`、`ANALYSIS_DB_ID`，並更新 module docstring
- Modify: `tests/test_export_sheet.py`：import 改指向 `ledger_analysis.export_sheet`，刪除 `test_save_data_writes_json_with_indent`、`test_main_reads_pages_and_writes_json`

**Interfaces:**
- Produces: `HEADER: list[str]`（等於 Global Constraints 裡的 header）
- Produces: `build_rows(months: dict[str, dict]) -> list[list]`。`months` 的形狀和 `page_to_month_entry` 回傳的 entry 相同：`{"202504": {"by_category": {...}, "by_funds": {...}, "total": n}}`

- [ ] **Step 1: 改名檔案並修正 import**

```bash
git mv ledger_analysis/export_json.py ledger_analysis/export_sheet.py
git mv tests/test_export_json.py tests/test_export_sheet.py
```

刪掉上面列出的函式和測試。

- [ ] **Step 2: 寫失敗的測試**

```python
from ledger_analysis.export_sheet import HEADER, build_rows

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
```

- [ ] **Step 3: 執行測試，確認失敗**

Run: `pytest tests/test_export_sheet.py -v`
Expected: 新的 3 個測試 FAIL（ImportError），其他測試 PASS

- [ ] **Step 4: 在 `export_sheet.py` 實作 `HEADER` 和 `build_rows`**

欄位順序依照 `CATEGORIES`、`FUND_FIELDS`，月份字串照原樣保留。

- [ ] **Step 5: 執行測試，確認通過**

Run: `pytest -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add -A ledger_analysis tests
git commit -m "refactor(export): rename export_json to export_sheet and add build_rows"
```

---

### Task 2: `post_rows` 和 `main`（POST 給 Web App）

**Files:**
- Modify: `ledger_analysis/export_sheet.py`
- Test: `tests/test_export_sheet.py`

**Interfaces:**
- Consumes: Task 1 的 `HEADER`、`build_rows`、`fetch_all_pages`、`page_to_month_entry`
- Produces: `post_rows(url: str, token: str, header: list[str], rows: list[list], opener=urllib.request.urlopen) -> dict`。成功時回傳解析後的 JSON；回應不是 JSON 或 `ok` 不為 true 時拋出 `RuntimeError`
- Produces: `main() -> None`。CLI 入口：`python ledger_analysis/export_sheet.py`

- [ ] **Step 1: 寫失敗的測試**

用假的 `opener` 回傳物件（有 `.read()`，回傳 bytes），不碰網路：

```python
import json, pytest
from unittest.mock import MagicMock
from ledger_analysis import export_sheet

def _resp(body: str):
    r = MagicMock(); r.read.return_value = body.encode("utf-8")
    r.__enter__.return_value = r; r.__exit__.return_value = False
    return r

def test_post_rows_sends_token_header_rows_as_json():
    captured = {}
    def opener(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["ctype"] = req.headers.get("Content-type")
        return _resp('{"ok": true, "rows": 1}')
    out = export_sheet.post_rows("https://x", "tok", ["月份"], [["202501"]], opener=opener)
    assert out == {"ok": True, "rows": 1}
    assert captured["body"] == {"token": "tok", "header": ["月份"], "rows": [["202501"]]}
    assert captured["ctype"] == "application/json"

def test_post_rows_raises_when_ok_false():
    opener = lambda req, timeout=None: _resp('{"ok": false, "error": "unauthorized"}')
    with pytest.raises(RuntimeError, match="unauthorized"):
        export_sheet.post_rows("https://x", "bad", [], [], opener=opener)

def test_post_rows_raises_on_non_json_response():
    opener = lambda req, timeout=None: _resp("<html>Sign in</html>")
    with pytest.raises(RuntimeError, match="Sign in"):
        export_sheet.post_rows("https://x", "tok", [], [], opener=opener)

def test_main_requires_sheet_env_before_calling_notion(monkeypatch):
    monkeypatch.setenv("NOTION_SECRET", "n")
    monkeypatch.delenv("SHEET_WEBAPP_URL", raising=False)
    monkeypatch.setenv("SHEET_TOKEN", "t")
    api_cls = MagicMock()
    monkeypatch.setattr(export_sheet, "NotionApi", api_cls)
    with pytest.raises(KeyError):
        export_sheet.main()
    api_cls.assert_not_called()

def test_main_refuses_to_post_when_no_months(monkeypatch):
    for k, v in {"NOTION_SECRET": "n", "SHEET_WEBAPP_URL": "u", "SHEET_TOKEN": "t"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(export_sheet, "NotionApi", MagicMock())
    monkeypatch.setattr(export_sheet, "fetch_all_pages", lambda api, db: [])
    post = MagicMock()
    monkeypatch.setattr(export_sheet, "post_rows", post)
    with pytest.raises(SystemExit):
        export_sheet.main()
    post.assert_not_called()

def test_main_posts_sorted_rows(monkeypatch):
    for k, v in {"NOTION_SECRET": "n", "SHEET_WEBAPP_URL": "u", "SHEET_TOKEN": "t"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(export_sheet, "NotionApi", MagicMock())
    pages = [_make_page("202502", total=2), _make_page("202501", total=1)]  # 既有 helper
    monkeypatch.setattr(export_sheet, "fetch_all_pages", lambda api, db: pages)
    post = MagicMock(return_value={"ok": True, "rows": 2})
    monkeypatch.setattr(export_sheet, "post_rows", post)
    export_sheet.main()
    url, token, header, rows = post.call_args.args
    assert (url, token, header) == ("u", "t", export_sheet.HEADER)
    assert [r[0] for r in rows] == ["202501", "202502"]
    assert [r[-1] for r in rows] == [1, 2]
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `pytest tests/test_export_sheet.py -v`
Expected: 新的測試 FAIL（AttributeError: post_rows / main）

- [ ] **Step 3: 實作 `post_rows` 和 `main`**

- `post_rows`：用 `urllib.request.Request(url, data=..., headers={"Content-Type": "application/json"}, method="POST")`，timeout 設 60 秒。`urlopen` 預設會跟著 Apps Script 的 302 轉址。`json.loads` 失敗時拋出 `RuntimeError`，訊息附上回應的前 200 字
- `main`：先讀 `os.environ["SHEET_WEBAPP_URL"]`、`os.environ["SHEET_TOKEN"]`、`os.environ["NOTION_SECRET"]`，再呼叫 Notion。months 為空時 `sys.exit("No months found in analysis DB; refusing to overwrite sheet")`。最後印出 `Wrote {n} months to sheet: {first}..{last}`
- 檔尾的 `if __name__ == "__main__": main()` 保留

- [ ] **Step 4: 執行測試，確認通過**

Run: `pytest -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add ledger_analysis/export_sheet.py tests/test_export_sheet.py
git commit -m "feat(export): post monthly rows to Apps Script web app"
```

---

### Task 3: Apps Script Web App（repo 內副本 + 部署說明）

**Files:**
- Create: `apps_script/Code.gs`
- Create: `apps_script/README.md`（部署步驟）

**Interfaces:**
- Consumes: Task 2 送出的 JSON body `{"token", "header", "rows"}`
- Produces: 符合 Global Constraints 的回應格式

- [ ] **Step 1: 實作 `apps_script/Code.gs`**

- `const SHEET_NAME = "家庭月統計";`
- `doPost(e)`：用 `JSON.parse(e.postData.contents)` 解析 body。token 不等於 `PropertiesService.getScriptProperties().getProperty("SHEET_TOKEN")`，或 Script Property 沒設定時，回傳 `{ok:false, error:"unauthorized"}`
- 用 `SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME)` 找分頁，沒有就 `insertSheet(SHEET_NAME)`。接著 `sheet.clearContents()`，再用 `getRange(1, 1, 1 + rows.length, header.length).setValues([header, ...rows])` 寫入，並 `setFrozenRows(1)`
- 全部包在 try/catch 裡，例外時回傳 `{ok:false, error: String(err)}`
- 回應一律用 `ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON)`
- 月份欄要寫成文字，避免被 Sheets 轉成數字：寫入前把 A 欄設成 `setNumberFormat("@")`

- [ ] **Step 2: 寫 `apps_script/README.md`**

內容（繁體中文）：
1. 在「消費分析」試算表開「擴充功能 → Apps Script」，把 `Code.gs` 整份貼上
2. 專案設定 → 指令碼屬性，新增 `SHEET_TOKEN`，值用 `openssl rand -hex 32` 產生
3. 部署 → 新增部署作業 → 類型選「網頁應用程式」，執行身分選「我」，存取權選「任何人」，然後複製 Web App URL
4. GitHub repo secrets 新增 `SHEET_WEBAPP_URL`（上一步的 URL）和 `SHEET_TOKEN`（同第 2 步的值）
5. 本地驗證指令：

```bash
SHEET_WEBAPP_URL=... SHEET_TOKEN=... NOTION_SECRET=... python ledger_analysis/export_sheet.py
```

6. 修改 `Code.gs` 之後要「管理部署作業 → 編輯 → 新版本」，URL 會維持不變

- [ ] **Step 3: 手動驗證（使用者部署後執行）**

Run:

```bash
curl -sL "$SHEET_WEBAPP_URL" -H 'Content-Type: application/json' -d '{"token":"wrong","header":[],"rows":[]}'
```

Expected: `{"ok":false,"error":"unauthorized"}`，而且「家庭月統計」分頁沒有被建立或修改

- [ ] **Step 4: Commit**

```bash
git add apps_script
git commit -m "feat(sheet): add Apps Script web app for monthly stats"
```

---

### Task 4: Workflow 改寫 Sheet，移除網頁

**Files:**
- Modify: `.github/workflows/monthly-ledger-analysis.yml`
- Delete: `docs/index.html`、`docs/main.js`
- Modify: `.gitignore`（移除 `docs/data.json` 那兩行）
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2 的 CLI `python ledger_analysis/export_sheet.py`，以及 Task 3 的 secrets 名稱

- [ ] **Step 1: 修改 workflow**

- 把「Export JSON」步驟改名為「Export to Google Sheet」，執行 `python ledger_analysis/export_sheet.py`，env 帶入 `NOTION_SECRET`、`SHEET_WEBAPP_URL: ${{ secrets.SHEET_WEBAPP_URL }}`、`SHEET_TOKEN: ${{ secrets.SHEET_TOKEN }}`
- 刪除 Configure Pages、Upload Pages artifact、Deploy to GitHub Pages 三個步驟
- 刪除 job 的 `environment` 區塊，以及最上層的 `concurrency`
- `permissions` 只留 `contents: read`

- [ ] **Step 2: 刪除網頁檔案**

```bash
git rm docs/index.html docs/main.js
```

- [ ] **Step 3: 更新 README**

- 第 2 節的步驟 2、3 改成「跑 `export_sheet.py`：把 Notion『分析』DB 的所有月份寫進『消費分析』試算表的『家庭月統計』分頁」
- 第 3 節「視覺化頁面」改成「Google Sheet」：附上試算表連結，說明圖表在試算表裡手動建立
- 初次設定：刪除 Pages 那一步，改成指向 `apps_script/README.md`，並新增兩個 secrets
- 本地測試指令和目錄結構同步更新（`export_sheet.py`、`apps_script/`，移除 `docs/index.html`、`main.js`、`data.json`）

- [ ] **Step 4: 驗證**

Run: `pytest -v && grep -rni "export_json\|data\.json\|main\.js\|deploy-pages\|upload-pages\|github pages" README.md .github/ ledger_analysis/ tests/ || echo clean`
Expected: 測試全部 PASS，grep 輸出 `clean`

- [ ] **Step 5: Commit**

```bash
git add -A .github docs README.md .gitignore
git commit -m "feat: replace GitHub Pages dashboard with Google Sheet export"
```

---

### Task 5: 上線（使用者手動）

- [ ] 照 `apps_script/README.md` 部署 Web App，並設定 secrets
- [ ] 執行 Task 3 Step 3 的 curl 驗證
- [ ] 到 GitHub Actions 用 `workflow_dispatch` 手動跑一次 workflow。注意：這也會跑 `ledger_analysis.py`，會建立上個月的分析、關帳和開帳記錄。如果上個月已經結過帳，改成在本地只跑 `export_sheet.py`
- [ ] 確認「家庭月統計」分頁有所有歷史月份，奧捷兩個分頁沒變
- [ ] repo Settings → Pages 停用
- [ ] 在試算表裡建立需要的圖表
