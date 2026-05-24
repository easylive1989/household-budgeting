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
- 年視圖:圓餅(年度分類佔比) / 長條(12 個月總支出) / 折線(累計支出趨勢)

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
