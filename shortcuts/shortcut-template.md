# iOS 捷徑：快速記帳

在 iPhone Shortcuts App 內手動建立一個叫「快速記帳」的捷徑，按下面步驟設定。

## 動作流程

| # | Shortcuts 動作 | 設定 |
|---|---|---|
| 1 | Choose from List | 清單：娛樂 / 飲食 / 日常用品 / 水電管理費 / 房屋相關 / 收入 / 其它 → 變數 `category` |
| 2 | Ask for Input | Input Type: Number；提示：「金額（正數）？」→ 變數 `amount` |
| 3 | Choose from List | 清單：Paul / Lily / 現金 / 銀行存款 → 變數 `payer` |
| 4 | Ask for Input | Input Type: Text；提示:「名目（例如店家名）？」→ 變數 `note` |
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
