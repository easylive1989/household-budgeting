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

/**
 * 在「家庭月統計」分頁右側建立圖表（手動在編輯器執行一次即可）。
 * 會先移除這個分頁上既有的圖表再重建，可重跑。
 * 範圍用整欄，之後每月新增的列會自動帶進圖表。
 */
function setupCharts() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) throw new Error("找不到分頁：" + SHEET_NAME);

  sheet.getCharts().forEach(function (c) { sheet.removeChart(c); });

  const col = 12; // L 欄，放在資料右側
  const common = function (builder, title, row) {
    return builder
      .setOption("title", title)
      .setOption("width", 760)
      .setOption("height", 360)
      .setOption("legend", { position: "top" })
      .setOption("hAxis", { slantedText: true, slantedTextAngle: 45 })
      .setNumHeaders(1)
      .setPosition(row, col, 0, 0)
      .build();
  };

  // 1. 每月分類支出（堆疊長條）：A 欄月份 + B:E 四個分類
  sheet.insertChart(common(
    sheet.newChart().asColumnChart().setStacked()
      .addRange(sheet.getRange("A:E"))
      .setOption("colors", ["#E57373", "#81C784", "#FFD54F", "#64B5F6"]),
    "每月分類支出", 1));

  // 2. 每月資金來源（堆疊長條）：A 欄月份 + F:I（Paul / Lily / 現金 / 銀行存款）
  sheet.insertChart(common(
    sheet.newChart().asColumnChart().setStacked()
      .addRange(sheet.getRange("A:A"))
      .addRange(sheet.getRange("F:I"))
      .setOption("colors", ["#5C6BC0", "#EC407A", "#8D6E63", "#26A69A"]),
    "每月資金來源", 20));

  // 3. 每月總額（折線）：A 欄月份 + J 欄總額
  sheet.insertChart(common(
    sheet.newChart().asLineChart()
      .addRange(sheet.getRange("A:A"))
      .addRange(sheet.getRange("J:J"))
      .setOption("colors", ["#455A64"])
      .setOption("pointSize", 4),
    "每月總額", 39));
}
