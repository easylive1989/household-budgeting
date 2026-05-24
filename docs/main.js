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

// ---- Monthly view ----
function renderMonthlyView(data, yyyymm) {
  destroyCharts();
  const month = data.months[yyyymm];
  if (!month) {
    setStatus(`${yyyymm} 沒有資料`);
    return;
  }
  setStatus(`月視圖：${yyyymm}（總額 ${month.total.toLocaleString()}）`);

  // --- Pie: by_category ---
  const cats = data.categories;
  chartInstances.pie = new Chart(document.getElementById("pie"), {
    type: "pie",
    data: {
      labels: cats,
      datasets: [{
        data: cats.map(c => month.by_category[c] || 0),
        backgroundColor: cats.map(c => CATEGORY_COLORS[c]),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyymm} 分類佔比` } },
    },
  });

  // --- Bar: by_funds (4 bars) ---
  const funds = Object.keys(month.by_funds);
  chartInstances.bar = new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
      labels: funds,
      datasets: [{
        label: "支出",
        data: funds.map(f => month.by_funds[f] || 0),
        backgroundColor: funds.map(f => FUND_COLORS[f] || "#999"),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyymm} 資金來源支出` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // --- Line: past 6 months category trend ---
  const allMonths = Object.keys(data.months).sort();
  const idx = allMonths.indexOf(yyyymm);
  const window = allMonths.slice(Math.max(0, idx - 5), idx + 1); // up to 6 months ending at yyyymm
  chartInstances.line = new Chart(document.getElementById("line"), {
    type: "line",
    data: {
      labels: window,
      datasets: cats.map(c => ({
        label: c,
        data: window.map(m => (data.months[m].by_category[c] || 0)),
        borderColor: CATEGORY_COLORS[c],
        backgroundColor: CATEGORY_COLORS[c],
        tension: 0.2,
      })),
    },
    options: {
      plugins: { title: { display: true, text: `近 ${window.length} 個月分類趨勢` } },
      scales: { y: { beginAtZero: true } },
    },
  });
}
