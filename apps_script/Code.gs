/**
 * 「消費分析」試算表的 Web App：接收 GitHub Action 送來的每月統計，
 * 全量覆寫「家庭月統計」分頁。只碰這個分頁，其他分頁不動。
 *
 * Request body (JSON): {"token": "...", "header": [...], "rows": [[...], ...]}
 * Response (JSON):     {"ok": true, "rows": n} | {"ok": false, "error": "..."}
 *
 * repo 內的副本：apps_script/Code.gs。改完要貼回試算表並部署新版本。
 */

const SHEET_NAME = "家庭月統計";

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const expected = PropertiesService.getScriptProperties().getProperty("SHEET_TOKEN");
    if (!expected || body.token !== expected) {
      return reply_({ ok: false, error: "unauthorized" });
    }

    const header = body.header;
    const rows = body.rows;
    if (!Array.isArray(header) || header.length === 0 || !Array.isArray(rows)) {
      return reply_({ ok: false, error: "invalid payload" });
    }
    if (rows.some(function (r) { return !Array.isArray(r) || r.length !== header.length; })) {
      return reply_({ ok: false, error: "row length does not match header" });
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);

    sheet.clearContents();
    const values = [header].concat(rows);
    // 月份欄當文字，避免 202501 被轉成數字
    sheet.getRange(1, 1, values.length, 1).setNumberFormat("@");
    sheet.getRange(1, 1, values.length, header.length).setValues(values);
    sheet.setFrozenRows(1);

    return reply_({ ok: true, rows: rows.length });
  } catch (err) {
    return reply_({ ok: false, error: String(err) });
  }
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
