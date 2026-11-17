# 家庭記帳

家庭記帳工作流，由三部分組成：

## 1. Notion 帳本

- 共用帳本 DB：`43c59e00321e49a69d85037f0f45ba7e`
- 每月分析 DB：`25c8303f78f780fd9227e5e9d54c6b43`
- 欄位：`名目`（title）、`分類`（select）、`Paul` / `Lily` / `現金` / `銀行存款`（number）、`備註`（rich_text）、`時間`（formula）、`修正時間`（date）
- 慣例：支出記負、收入記正，每筆只填一個 number 欄位（Paul / Lily / 現金 / 銀行存款 擇一）

## 2. 自動月結（GitHub Action）

每月 1 號 UTC 0:00（台灣早上 8:00）自動執行 `.github/workflows/monthly-ledger-analysis.yml`，做：
1. 跑 `ledger_analysis/ledger_analysis.py`：算上月 4 大分類加總，產 mermaid 圖寫進「每月分析」DB；建立關帳（`修正時間` 記為上月最後一天 23:59 台灣時間，Notion 只存到分鐘）、開帳記錄
2. 跑 `ledger_analysis/export_sheet.py`：抓 Notion「分析」DB 所有月份，POST 給 Apps Script Web App，全量覆寫「消費分析」試算表的「家庭月統計」分頁

## 3. Google Sheet 統計

試算表：https://docs.google.com/spreadsheets/d/1yGqmUqYheFhM4VsbAptVyHp1k3InpV6GdiPjI_zSzFw/edit

- 「家庭月統計」分頁：每月一列，欄位 `月份 | 娛樂 | 飲食 | 日常用品 | 水電管理費 | Paul | Lily | 現金 | 銀行存款 | 總額`
- 每次執行會整頁重寫，請勿在此分頁手動編輯；圖表請在試算表內建立，範圍指向整欄
- Web App 程式與部署步驟見 `apps_script/README.md`

## 4. iOS 捷徑

照 `shortcuts/shortcut-template.md` 在 iPhone Shortcuts App 手動建立。

## 初次設定

1. Repo Settings → Secrets and variables → Actions → New repository secret
   - Name: `NOTION_SECRET`
   - Value: 從 Notion → My integrations 取得的 token
2. 照 `apps_script/README.md` 部署 Web App，並新增 secrets `SHEET_WEBAPP_URL`、`SHEET_TOKEN`
3. 在 iPhone 照 `shortcuts/shortcut-template.md` 建立捷徑
4. 本地測試（可選）：
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   export NOTION_SECRET="<your-token>"
   export SHEET_WEBAPP_URL="<web-app-url>"
   export SHEET_TOKEN="<sheet-token>"
   python ledger_analysis/export_sheet.py   # 寫入「家庭月統計」分頁
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
│   └── export_sheet.py         # 匯出到 Google Sheet
├── apps_script/
│   ├── Code.gs                 # 試算表 Web App（副本，需手動貼回部署）
│   └── README.md               # 部署步驟
├── docs/superpowers/           # 設計與計畫文件
├── shortcuts/
│   └── shortcut-template.md
└── tests/
    ├── test_notion.py
    └── test_export_sheet.py
```
