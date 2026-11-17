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

const CHART_DATA_SHEET = "圖表資料";
const CHART_MONTHS = 12;

/**
 * 在「家庭月統計」分頁右側建立「每月分類佔比」圖表（手動在編輯器執行一次即可）。
 * 100% 堆疊長條：每月一根，四個分類依佔比切分，大額月份不會壓扁其他月份。
 *
 * 只顯示最新 12 個月：doPost 每次會清空「家庭月統計」，所以公式放在隱藏分頁
 * 「圖表資料」，用 QUERY 取最新 12 個月再依時間排序，新月份寫入後自動往後滾。
 * 會先移除既有圖表、重寫公式再重建，可重跑。
 */
function setupCharts() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) throw new Error("找不到分頁：" + SHEET_NAME);

  const data = ss.getSheetByName(CHART_DATA_SHEET) || ss.insertSheet(CHART_DATA_SHEET);
  data.clear();
  // 第 1 列：標題；第 2 列起：最新 N 個月，依月份由舊到新
  data.getRange("A1").setFormula(
    "={'" + SHEET_NAME + "'!A1:E1; SORT(QUERY('" + SHEET_NAME + "'!A2:E, " +
    "\"select * where A is not null order by A desc limit " + CHART_MONTHS + "\", 0), 1, TRUE)}"
  );
  data.hideSheet();

  sheet.getCharts().forEach(function (c) { sheet.removeChart(c); });

  // 月份 + 四個分類（娛樂 / 飲食 / 日常用品 / 水電管理費）
  const chart = sheet.newChart().asColumnChart()
    .addRange(data.getRange(1, 1, CHART_MONTHS + 1, 5))
    .setNumHeaders(1)
    .setHiddenDimensionStrategy(Charts.ChartHiddenDimensionStrategy.SHOW_BOTH)
    .setOption("isStacked", "percent")
    .setOption("title", "每月分類佔比（最近 " + CHART_MONTHS + " 個月）")
    .setOption("width", 1000)
    .setOption("height", 440)
    .setOption("legend", { position: "top" })
    .setOption("hAxis", { slantedText: true, slantedTextAngle: 45 })
    .setOption("colors", ["#E57373", "#81C784", "#FFD54F", "#64B5F6"])
    .setPosition(1, 12, 0, 0) // L1，放在資料右側
    .build();
  sheet.insertChart(chart);
}
