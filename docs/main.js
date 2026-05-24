// ---- Color palette (synced with ledger_analysis.py mermaid colors) ----
const CATEGORY_COLORS = {
  娛樂: "#FF0000",
  日常用品: "#FFFF00",
  飲食: "#00FF00",
  水電管理費: "#0000FF",
};

// ---- State ----
let chartInstances = { pie: null, bar: null, line: null };

// ---- Data loading ----
async function loadData() {
  const resp = await fetch("./data.json", { cache: "no-store" });
  if (!resp.ok) throw new Error(`Failed to load data.json: ${resp.status}`);
  return await resp.json();
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

// ---- Yearly view ----
function renderYearlyView(data, yyyy) {
  destroyCharts();
  const monthsInYear = Object.keys(data.months)
    .filter(m => m.startsWith(yyyy))
    .sort();
  if (monthsInYear.length === 0) {
    setStatus(`${yyyy} 沒有資料`);
    return;
  }

  const cats = data.categories;

  // Aggregate by_category for the full year
  const yearCat = Object.fromEntries(cats.map(c => [c, 0]));
  let yearTotal = 0;
  for (const m of monthsInYear) {
    for (const c of cats) {
      yearCat[c] += data.months[m].by_category[c] || 0;
    }
    yearTotal += data.months[m].total || 0;
  }
  setStatus(`${yyyy} 年（總額 ${yearTotal.toLocaleString()}）`);

  // 12-month slots — null for months without data (未到的月份)
  const months12 = Array.from({ length: 12 }, (_, i) => `${yyyy}${String(i+1).padStart(2,"0")}`);

  // --- Pie: yearly category proportions ---
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
      responsive: true,
      maintainAspectRatio: false,
      plugins: { title: { display: true, text: `${yyyy} 年度分類佔比` } },
    },
  });

  // --- Bar: cumulative spending (running total through each month) ---
  let running = 0;
  const cumulative = months12.map(m => {
    if (data.months[m]) {
      running += data.months[m].total;
      return running;
    }
    return null; // no bar for future months
  });
  chartInstances.bar = new Chart(document.getElementById("bar"), {
    type: "bar",
    data: {
      labels: months12.map(m => m.slice(4)),
      datasets: [{
        label: "累積支出",
        data: cumulative,
        backgroundColor: "#2c5aa0",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { title: { display: true, text: `${yyyy} 累積支出` }, legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // --- Line: 4 categories, monthly spend, straight lines, no points on future months ---
  chartInstances.line = new Chart(document.getElementById("line"), {
    type: "line",
    data: {
      labels: months12.map(m => m.slice(4)),
      datasets: cats.map(c => ({
        label: c,
        data: months12.map(m => data.months[m] ? (data.months[m].by_category[c] || 0) : null),
        borderColor: CATEGORY_COLORS[c],
        backgroundColor: CATEGORY_COLORS[c],
        tension: 0,        // straight lines
        spanGaps: false,    // don't connect across null (future) months
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { title: { display: true, text: `${yyyy} 各分類每月支出` } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

// ---- UI controller ----
function setupUI(data) {
  const select = document.getElementById("period-select");

  function populateSelect() {
    const years = getYears(data);
    select.innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join("");
  }

  function render() {
    const year = select.value;
    if (!year) return;
    renderYearlyView(data, year);
  }

  select.addEventListener("change", render);
  populateSelect();
  render();
}

// ---- Bootstrap ----
(async () => {
  try {
    const data = await loadData();
    setupUI(data);
  } catch (err) {
    console.error(err);
    setStatus(`載入失敗：${err.message}`);
  }
})();
