# Apps Script Web App 部署

GitHub Action 每月跑 `ledger_analysis/export_sheet.py`，把 Notion「分析」DB 的所有月份 POST 到這個 Web App，再由它全量覆寫「消費分析」試算表的「家庭月統計」分頁。

試算表：https://docs.google.com/spreadsheets/d/1yGqmUqYheFhM4VsbAptVyHp1k3InpV6GdiPjI_zSzFw/edit

## 初次部署

1. 開啟試算表，點「擴充功能 → Apps Script」，把 `Code.gs` 整份貼上，覆蓋預設內容後存檔
2. 產生驗證用的 token：

   ```bash
   openssl rand -hex 32
   ```

   接著到「專案設定 → 指令碼屬性」新增一筆屬性，名稱填 `SHEET_TOKEN`，值填剛剛產生的 token
3. 點「部署 → 新增部署作業」，類型選「網頁應用程式」，設定如下：
   - 執行身分：我
   - 誰可以存取：任何人（未帶正確 token 的請求會被拒絕）

   第一次部署時會跳出授權畫面，請允許存取試算表。部署完成後，複製 Web App 網址（`https://script.google.com/macros/s/.../exec`）
4. 到 GitHub repo 的「Settings → Secrets and variables → Actions」新增兩個 secret：
   - `SHEET_WEBAPP_URL`：上一步複製的網址
   - `SHEET_TOKEN`：第 2 步產生的 token

## 驗證

先確認 token 錯誤時會被拒絕，而且分頁不會被改動：

```bash
curl -sL -X POST "$SHEET_WEBAPP_URL" -H 'Content-Type: application/json' -d '{"token":"wrong","header":[],"rows":[]}'
```

預期回應是 `{"ok":false,"error":"unauthorized"}`。

再實際寫入一次：

```bash
SHEET_WEBAPP_URL=... SHEET_TOKEN=... NOTION_SECRET=... python ledger_analysis/export_sheet.py
```

## 修改程式之後

1. 把新的 `Code.gs` 貼回 Apps Script 編輯器並存檔
2. 點「部署 → 管理部署作業 → 編輯（鉛筆圖示）」，版本選「新版本」後部署

用這個方式更新，Web App 網址會維持不變，GitHub secret 不用改。
