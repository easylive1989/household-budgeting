# 每月統計改寫進 Google Sheet（取代 GitHub Pages 網頁）

## 目的

每月統計原本匯出成 `docs/data.json`，再由 GitHub Pages 網頁（https://paul-learning.dev/household-budgeting/）畫圖。
改成把每月統計寫進 Google 試算表「消費分析」，直接在試算表裡看，網頁不再使用。

- 試算表：https://docs.google.com/spreadsheets/d/1yGqmUqYheFhM4VsbAptVyHp1k3InpV6GdiPjI_zSzFw/edit

## 目標 / 非目標

- 目標：每月 1 號月結完成後，自動把 Notion「分析」DB 的全部月份寫進試算表的「家庭月統計」分頁
- 目標：不使用 Google service account，也不需要建立 Google Cloud 專案
- 非目標：記帳方式不變，iOS 捷徑和 Notion 帳本都不動
- 非目標：`ledger_analysis.py` 的月結邏輯不動，包含關帳、開帳記錄，以及寫進 Notion「分析」DB 的內容和 mermaid 圖
- 反目標：不能動到試算表裡現有的「2026奧捷原始記錄」和「2026奧捷分析」兩個分頁

## 考慮過的做法

| 做法 | 取捨 | 結果 |
|------|------|------|
| A. GitHub Action 用 service account 寫 Sheet | 程式全在 repo，但要開 Google Cloud 專案並管理金鑰 | 使用者不想用 service account |
| B. 試算表的 Apps Script 定時自己抓 Notion | 不用 Google Cloud，但只能靠時間錯開排在月結之後，月結失敗時它也不知道 | 未選 |
| C. GitHub Action POST 給 Apps Script Web App | 不用 Google Cloud，月結後立刻寫入，失敗時 Action 會報錯；Apps Script 程式要手動部署 | **選用** |
| D. 試算表用 `IMPORTDATA` 讀公開的 CSV | 最簡單，但家庭支出資料要放在公開網址 | 未選 |

## 設計

### 資料流

```
Notion 分析 DB ──(GitHub Action: export_sheet.py)──POST JSON──▶ Apps Script Web App ──▶「家庭月統計」分頁
```

### Python 端（`ledger_analysis/export_sheet.py`）

- 沿用 `export_json.py` 的 `fetch_all_pages`、`page_to_month_entry`，從 Notion「分析」DB 讀出所有 `YYYYMM` 月份
- 把月份依時間排序，組成 rows：`[月份, 娛樂, 飲食, 日常用品, 水電管理費, Paul, Lily, 現金, 銀行存款, 總額]`
- POST JSON `{"token": ..., "header": [...], "rows": [...]}` 到 `SHEET_WEBAPP_URL`
- 回應不是 `{"ok": true}` 時以非 0 exit code 結束，讓 Action 顯示失敗
- 數值照 Notion「分析」DB 裡的值原樣寫入，不做正負號轉換
- `export_json.py` 和 `docs/data.json` 的匯出移除

### Apps Script 端（`apps_script/Code.gs`，repo 內留副本）

- `doPost(e)`：解析 JSON，比對 token 是否等於 Script Properties 的 `SHEET_TOKEN`；不符就回 `{"ok": false, "error": "unauthorized"}`
- 找不到「家庭月統計」分頁就自動建立；找到就清空內容後重寫 header 和全部 rows（全量覆寫，可重跑）
- 只操作「家庭月統計」分頁
- 部署設定：執行身分「我」，存取權「任何人」（靠 token 擋未授權的呼叫）

### GitHub Action

- 「Export JSON」步驟換成 `python ledger_analysis/export_sheet.py`，帶入 secrets `SHEET_WEBAPP_URL`、`SHEET_TOKEN`
- 移除 Pages 相關的步驟（configure / upload / deploy）、`pages`/`id-token` 權限、`environment`、`concurrency: pages`

### 網頁移除

- 刪除 `docs/index.html`、`docs/main.js`
- `docs/superpowers/` 規格文件保留
- README 更新：移除 Pages 說明，新增 Apps Script 部署和 secrets 設定步驟
- 使用者手動到 repo Settings → Pages 停用（停用後 paul-learning.dev/household-budgeting/ 會變成 404）

## 留給實作者判斷的部分（皆為 Claude 的提議）

- 圖表：使用者在試算表裡手動建一次（圓餅、長條、折線），範圍指向整欄，之後新增的月份會自動帶進去。腳本不負責畫圖
- 年度彙總：第一版不做，需要時可以在試算表裡用樞紐分析表或公式處理
- HTTP 呼叫用標準庫 `urllib`，不新增依賴。Apps Script Web App 回 302 轉址時，要跟著轉址拿回應
- 上線前先用 `workflow_dispatch` 手動跑一次，確認歷史月份都有補齊
