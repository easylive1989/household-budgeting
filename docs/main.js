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

// ---- Yearly view ----
function renderYearlyView(data, yyyy) {
  destroyCharts();
  // Collect all months belonging to that year
  const monthsInYear = Object.keys(data.months)
    .filter(m => m.startsWith(yyyy))
    .sort();
  if (monthsInYear.length === 0) {
    setStatus(`${yyyy} 沒有資料`);
    return;
  }

  // Aggregate by_category for the year
  const cats = data.categories;
  const yearCat = Object.fromEntries(cats.map(c => [c, 0]));
  let yearTotal = 0;
  for (const m of monthsInYear) {
    for (const c of cats) {
      yearCat[c] += data.months[m].by_category[c] || 0;
    }
    yearTotal += data.months[m].total || 0;
  }
  setStatus(`年視圖:${yyyy}（總額 ${yearTotal.toLocaleString()}）`);

  // --- Pie: yearly by_category ---
  chartInstances.pie = new Chart(document.getElementById("pie"), {
    type: "pie",
    data: {
      labels: cats,
      datasets: [{
        data: cats.map(c => yearCat[c]),
        backgroundColor: cats.map(c => CATEGORY_COLORS[c]),
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 年度分類佔比` } },
    },
  });

  // --- Bar: 12 months total ---
  const months12 = Array.from({ length: 12 }, (_, i) => `${yyyy}${String(i+1).padStart(2,"0")}`);
  const monthTotals = months12.map(m => (data.months[m] ? data.months[m].total : 0));
  chartInstances.bar = new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
      labels: months12.map(m => m.slice(4)), // "01"..."12"
      datasets: [{
        label: "每月總支出",
        data: monthTotals,
        backgroundColor: "#2c5aa0",
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 每月總支出` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // --- Line: cumulative total ---
  let running = 0;
  const cumulative = monthTotals.map(v => (running += v));
  chartInstances.line = new Chart(document.getElementById("line"), {
    type: "line",
    data: {
      labels: months12.map(m => m.slice(4)),
      datasets: [{
        label: "累計支出",
        data: cumulative,
        borderColor: "#c0392b",
        backgroundColor: "#c0392b",
        tension: 0.2,
      }],
    },
    options: {
      plugins: { title: { display: true, text: `${yyyy} 累計支出趨勢` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}
