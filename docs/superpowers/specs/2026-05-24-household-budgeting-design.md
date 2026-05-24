# 家庭記帳專案 Design Spec

**日期**：2026-05-24
**作者**：Paul Wu
**狀態**：草稿，待 review

## 目標

把現有「Notion 帳本 + 月度分析腳本」工作流完整化，加上視覺化頁面與 iOS 快速記帳，
變成可長期自用的家庭記帳系統。

**範圍**：先做個人版（欄位寫死 Paul/Lily/現金/銀行存款）。日後若要分享給別人複製，再做
schema 抽象、Notion template、複製教學等。

## 現況

- Notion「共用帳本」DB (`43c59e00321e49a69d85037f0f45ba7e`) 已存在，schema 確認過：
  - title: `名目`、select: `分類`、rich_text: `備註`、formula: `時間`、date: `修正時間`
  - number: `Paul`、`Lily`、`現金`、`銀行存款`
  - 慣例：支出記負、每筆只填一個 number 欄位
  - `時間` formula = `if(empty(修正時間), Created time, 修正時間)`
- Notion「每月分析」DB (`25c8303f78f780fd9227e5e9d54c6b43`) 已存在，僅一個 `Name` title 欄位
- `ledger_analysis/ledger_analysis.py` 已寫好（月度關帳/開帳 + mermaid pie 寫入分析 DB）
- `.github/workflows/monthly-ledger-analysis.yml` 已設好每月 1 號 UTC 0:00 觸發
- **缺失**：`common/notion.py` 被 import 但不存在，目前 workflow 應該沒成功跑過

## 目標架構

```
household-budgeting/
├── common/
│   └── notion.py             # 新：NotionApi class，wrap notion-client SDK
├── ledger_analysis/
│   ├── ledger_analysis.py    # 既有，零變動
│   └── export_json.py        # 新：產 docs/data.json
├── docs/                     # GitHub Pages root
│   ├── index.html            # 新
│   ├── main.js               # 新
│   └── data.json             # 新（Action 寫入）
├── shortcuts/
│   ├── README.md             # 新：捷徑設計說明
│   └── shortcut-template.md  # 新：對照在 iOS Shortcuts App 手動建立的規格
├── .github/workflows/
│   └── monthly-ledger-analysis.yml  # 修：加 export_json + commit & push
├── requirements.txt          # 新：notion-client
└── README.md                 # 新：個人用簡單版
```

**設計原則**

- 既有 `ledger_analysis.py` 零變動（即使內部 import 路徑、helper 簽名也不動）
- 新功能完全隔離在獨立模組（`export_json.py`、`docs/`、`shortcuts/`）
- 一次 Action run 串起所有事：關帳/開帳/Mermaid → 匯出 JSON → commit & push

## 模組設計

### 1. `common/notion.py`

提供 `NotionApi` class，介面與 `ledger_analysis.py` 既有用法相容，內部改用 `notion-client` SDK：

```python
from notion_client import Client, APIResponseError

class _FakeResp:
    """讓 SDK 結果具備 ledger_analysis.py 期望的 .status_code 與 .json() 介面"""
    def __init__(self, status, data):
        self.status_code, self._data = status, data
    def json(self):
        return self._data

class NotionApi:
    def __init__(self, token):
        self.client = Client(auth=token)

    def query_database(self, db_id, filter_body):
        try:
            return _FakeResp(200, self.client.databases.query(database_id=db_id, **filter_body))
        except APIResponseError as e:
            return _FakeResp(e.status, {"error": str(e)})

    def create_page(self, db_id, properties):
        try:
            return _FakeResp(200, self.client.pages.create(
                parent={"database_id": db_id}, properties=properties))
        except APIResponseError as e:
            return _FakeResp(e.status, {"error": str(e)})

    def append_block_children(self, page_id, blocks):
        try:
            return _FakeResp(200, self.client.blocks.children.append(
                block_id=page_id, children=blocks))
        except APIResponseError as e:
            return _FakeResp(e.status, {"error": str(e)})

    def get_property_names_by_type(self, db_id, types):
        """從 DB schema 回傳 {type: property_name} dict"""
        db = self.client.databases.retrieve(database_id=db_id)
        out = {}
        for name, prop in db["properties"].items():
            if prop["type"] in types:
                out[prop["type"]] = name
        return out

    def check_record_exists(self, db_id, title_prop_name, value):
        """檢查指定 title 值是否已存在"""
        resp = self.client.databases.query(
            database_id=db_id,
            filter={"property": title_prop_name, "title": {"equals": value}}
        )
        return len(resp["results"]) > 0
```

注意：`_FakeResp` 只是相容層；新程式碼建議直接用 `self.client` 屬性，不過 wrapper。

### 2. `ledger_analysis/export_json.py`

**職責**：讀 Notion 帳本，更新 `docs/data.json`，內容覆蓋上個月。

**JSON schema**：

```json
{
  "generated_at": "2025-05-01T00:30:00+08:00",
  "categories": ["娛樂", "飲食", "日常用品", "水電管理費"],
  "members": ["Paul", "Lily"],
  "months": {
    "202504": {
      "by_category": {
        "娛樂": 1200,
        "飲食": 8500,
        "日常用品": 2300,
        "水電管理費": 3000
      },
      "by_funds": {
        "Paul": 4000,
        "Lily": 3000,
        "現金": 2000,
        "銀行存款": 6000
      },
      "total": 15000
    }
  }
}
```

**規則**：
- 一份檔含所有歷史月份，新月份合併進現有 `months`，**舊月份不重算**
- 金額一律轉正號（顯示用），雖然 Notion 內部記負
- `by_category` 只統計 4 個固定分類（與現有 mermaid 一致），排除「財務整理」「收入」「房屋相關」「其它」「其他」
- `by_funds` 統計 4 個資金來源欄位的支出（Paul/Lily/現金/銀行存款）。現有資料每筆只填一個欄位，所以 `sum(by_funds.values()) == sum(by_category.values()) == total`
- `total` = `sum(by_category.values())`（也等於 `sum(by_funds.values())`）
- 重跑同月份會覆蓋既有值（idempotent）

**演算法**：
1. 讀 `docs/data.json`（若存在），取 `months` 物件；若不存在，初始為 `{}`
2. 計算上月日期區間（沿用 `ledger_analysis.py` 相同邏輯）
3. 用 `NotionApi.query_database` 查上月 4 類交易（filter 同 `ledger_analysis.py` `filter_body_chart`）
4. 遍歷結果：
   - 對每筆 row，把 `Paul/Lily/現金/銀行存款` 4 欄取絕對值（null 視為 0）
   - 累加 `by_category[row.分類] += sum(那 4 個欄位的絕對值)`
   - 同時累加 `by_funds[欄位名] += 該欄位絕對值` for 4 個欄位
5. `total = sum(by_category.values())`
6. 更新 `months[YYYYMM]`，寫回 `docs/data.json`

### 3. `docs/index.html` + `docs/main.js`

**HTML 結構**：

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>家庭記帳分析</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  <style>/* 基礎 CSS，grid 排版 */</style>
</head>
<body>
  <header><h1>家庭記帳分析</h1></header>
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

**main.js 函式分組**（同檔內）：

| 函式 | 職責 |
|---|---|
| `loadData()` | fetch `data.json`，回傳 parsed object |
| `getMonths(data)` | 從 `data.months` keys 排序回傳 `["202504", "202503", ...]` |
| `getYears(data)` | 從 month keys 提取年份去重 |
| `renderMonthlyView(data, yyyymm)` | 渲染月視圖三圖 |
| `renderYearlyView(data, yyyy)` | 渲染年視圖三圖 |
| `setupUI(data)` | tab 切換、下拉選單事件繫結 |
| `chartInstances` | 全域 `{pie, bar, line}`，切換時 `.destroy()` 再重建 |

**圖表內容**：

月視圖（給定 YYYYMM）：
- Pie：該月 `by_category` 4 類佔比
- Bar：該月 `by_funds`，4 個 bar 各表 Paul / Lily / 現金 / 銀行存款 的支出
- Line：過去 6 個月（含當月）的 4 條分類折線，橫軸是月份，每條線一個分類

年視圖（給定 YYYY）：
- Pie：該年聚合 12 個月的 `by_category` 加總
- Bar：12 個 bar 表 1-12 月的 `total`
- Line：該年累計支出，橫軸 1-12 月，縱軸是「1 月到 N 月 total 的累加」

**配色**：先沿用 mermaid 配色一致性：
- 娛樂 = 紅（`#FF0000`）
- 日常用品 = 黃（`#FFFF00`）
- 飲食 = 綠（`#00FF00`）
- 水電管理費 = 藍（`#0000FF`）

### 4. Action workflow

`.github/workflows/monthly-ledger-analysis.yml` 修改：

```yaml
name: Monthly Ledger Analysis

on:
  schedule:
    - cron: '0 0 1 * *'
  workflow_dispatch:

permissions:
  contents: write  # 新增：要 push commit 回 main

jobs:
  ledger-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
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
          git diff --staged --quiet || git commit -m "chore: update data.json for $(date +%Y-%m)"
          git push
```

順序：先做關帳/開帳/Mermaid（會在帳本生兩筆新交易），再匯出 JSON（會把這兩筆當「財務整理」分類過濾掉，所以不影響 4 類加總）。

### 5. iOS 捷徑（手動建立）

`shortcuts/shortcut-template.md` 提供照著建立的規格：

**捷徑名稱**：快速記帳

**動作流程**：

| 步驟 | Shortcuts 動作 | 內容 |
|---|---|---|
| 1 | Choose from List | 清單：娛樂 / 飲食 / 日常用品 / 水電管理費 / 房屋相關 / 收入 / 其它 → 變數 `category` |
| 2 | Ask for Input (Number) | 提示：「金額（正數）？」→ 變數 `amount` |
| 3 | Choose from List | 清單：Paul / Lily / 現金 / 銀行存款 → 變數 `payer` |
| 4 | Ask for Input (Text) | 提示：「名目（例如店家名）？」→ 變數 `note` |
| 5 | Calculate | `amount × -1` → 變數 `signed_amount`（如果分類是「收入」則保持正號；用 If 判斷） |
| 6 | Get Contents of URL | POST `https://api.notion.com/v1/pages`，headers + body 見下 |
| 7 | Show Result | 成功顯示 ✅、失敗顯示錯誤 |

**POST headers**：
```
Authorization: Bearer <NOTION_SECRET>
Notion-Version: 2022-06-28
Content-Type: application/json
```

**POST body 模板**（變數替換）：
```json
{
  "parent": { "database_id": "43c59e00321e49a69d85037f0f45ba7e" },
  "properties": {
    "名目": { "title":  [{ "text": { "content": "<note>" } }] },
    "分類": { "select": { "name": "<category>" } },
    "<payer>": { "number": <signed_amount> }
  }
}
```

**Token 存放**：先寫死在 Shortcuts 的 Text action 裡。提醒：不要分享捷徑檔。

**為什麼 repo 不放 `.shortcut` 二進位檔**：那是 plist 格式，AI 無法生成可用版本，且日後修改不易維護。使用 markdown 規格 + 截圖照建是長期較好的維護方式。

### 6. README

簡單個人用版本，內容大致：

```markdown
# 家庭記帳

家庭記帳工作流，元件：

## Notion 帳本
- 共用帳本 DB: `43c59e00321e49a69d85037f0f45ba7e`
- 每月分析 DB: `25c8303f78f780fd9227e5e9d54c6b43`
- 欄位慣例（名目/分類/Paul/Lily/現金/銀行存款 + 金額負數記支出）

## 自動月結（GitHub Action）
- 每月 1 號 UTC 0:00 觸發
- 做三件事：寫月度分析頁面、關帳開帳、更新 docs/data.json

## 視覺化頁面（GitHub Pages）
- URL: <填 Pages 啟用後>
- 月視圖：圓餅(分類)、長條(成員)、折線(過去 6 個月分類趨勢)
- 年視圖：圓餅(分類)、長條(每月)、折線(累計趨勢)

## iOS 捷徑
- 手動建立，見 `shortcuts/shortcut-template.md`

## 初次設定
1. Set `NOTION_SECRET` in repo secrets
2. Settings → Pages → Source: main / docs
3. iOS Shortcut: 照 `shortcuts/shortcut-template.md` 建立
```

### 7. requirements.txt

```
notion-client>=2.0.0
```

## 測試策略

| 元件 | 測試方式 |
|---|---|
| `common/notion.py` | pytest unit tests + 用 `responses` 或 `unittest.mock` mock SDK |
| `export_json.py` | pytest unit tests：給定假 Notion query 結果，驗證 JSON 輸出結構 |
| `ledger_analysis.py` | 不寫新測試（零變動，沿用既有信心） |
| `docs/main.js` | 無自動化（YAGNI），手動 smoke check：開頁、切 tab、切下拉、看三圖 |
| iOS 捷徑 | 手動：在 Notion DB 確認新紀錄欄位正確 |
| Action 流程 | 手動 `workflow_dispatch` 觸發後 inspect logs + Notion DB + docs/data.json |

## 邊界條件

- **第一次跑（沒有 `docs/data.json`）**：`export_json.py` 自行建立空殼，寫入該月份
- **`data.json` 損壞**：Action 該步驟會 fail，停在那邊不 push 任何東西，靠 GitHub 通知處理
- **單月無交易**：使用者表態不會發生（關帳/開帳本身就會生交易），不做防禦
- **重跑同月份**：覆寫該月份的值（idempotent），git diff 若為零則 commit 守門擋下不 push

## 不在這版範圍

- 給別人複製的 Notion template、設定教學
- schema 動態偵測（成員數量、帳戶數量、分類清單）
- 認證機制（前端輸入 token）
- 即時資料（前端跑 Notion API）
- 預算功能、提醒、跨幣別、發票辨識等
- 圖表互動（hover、drill-down）、深淺色主題切換、行動裝置適配

## 開放問題

1. **長條圖維度修正**：brainstorming 階段使用者說「長條看每位成員負擔」（Paul/Lily），但 self-review 發現
   現有資料每筆只填 1 個 number 欄位（4 欄是 fund source 池，非「成員 vs 帳戶」兩維度）。所以「成員負擔」
   語意對不上資料。spec 已改為「4 個資金來源支出」4 個 bar（Paul/Lily/現金/銀行存款），這樣 `by_funds`
   與 `by_category` 加總對齊，圖表也更貼近現有資料模式。如果這偏離本意，請 review 時提出。

2. **既有 `ledger_analysis.py` 的 formula filter 待驗證**：腳本對「時間」欄位的 filter 寫成
   `{"property": "時間", "date": {...}}`，但「時間」是 formula 型別，Notion API 標準語法應該是
   `{"property": "時間", "formula": {"date": {...}}}`。若實測發現 query 回傳空，
   implementation 階段需修正（這違反「既有腳本零變動」承諾，但若沒這修正整個 workflow 從未真的跑通）。
   `export_json.py` 會用驗證過後的正確 filter。
