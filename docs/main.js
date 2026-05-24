// ---- Color palette (synced with ledger_analysis.py mermaid colors) ----
const CATEGORY_COLORS = {
  娛樂: "#FF0000",
  日常用品: "#FFFF00",
  飲食: "#00FF00",
  水電管理費: "#0000FF",
};
const FUND_COLORS = {
  Paul: "#4E79A7",
  Lily: "#F28E2B",
  現金: "#59A14F",
  銀行存款: "#76B7B2",
};

// ---- State ----
let chartInstances = { pie: null, bar: null, line: null };

// ---- Data loading ----
async function loadData() {
  const resp = await fetch("./data.json", { cache: "no-store" });
  if (!resp.ok) throw new Error(`Failed to load data.json: ${resp.status}`);
  return await resp.json();
}

function getMonths(data) {
  return Object.keys(data.months).sort().reverse(); // newest first
}

function getYears(data) {
  const years = new Set();
  for (const yyyymm of Object.keys(data.months)) {
    years.add(yyyymm.slice(0, 4));
  }
  return [...years].sort().reverse();
}

function destroyCharts() {
  for (const k of Object.keys(chartInstances)) {
    if (chartInstances[k]) {
      chartInstances[k].destroy();
      chartInstances[k] = null;
    }
  }
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}
