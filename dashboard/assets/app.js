const API_BASE = window.PARKEE_API_BASE || "http://localhost:8000";

const style = getComputedStyle(document.documentElement);
const color = (name) => style.getPropertyValue(name).trim();

const SERIES = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => color(`--series-${i}`));
const TEXT_SECONDARY = color("--text-secondary");
const GRID = color("--grid");
const AXIS = color("--axis");

Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";
Chart.defaults.color = TEXT_SECONDARY;
Chart.defaults.borderColor = GRID;

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function commonScales(extra = {}) {
  return {
    x: { grid: { color: GRID }, ticks: { color: TEXT_SECONDARY }, ...extra.x },
    y: { grid: { color: GRID }, ticks: { color: TEXT_SECONDARY }, border: { color: AXIS }, ...extra.y },
  };
}

function groupBy(rows, key) {
  const map = new Map();
  for (const row of rows) {
    const k = row[key];
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(row);
  }
  return map;
}

// Q1 — top products by category (grouped bar per category)
async function renderTopProductsByCategory() {
  const rows = await getJSON("/api/top-products-by-category");
  const byCategory = groupBy(rows, "category");
  const categories = [...byCategory.keys()];
  const maxN = 5;

  const datasets = Array.from({ length: maxN }, (_, i) => ({
    label: `#${i + 1}`,
    data: categories.map((cat) => {
      const items = byCategory.get(cat).sort((a, b) => b.total_quantity - a.total_quantity);
      return items[i] ? items[i].total_quantity : 0;
    }),
    backgroundColor: SERIES[i % SERIES.length],
    borderRadius: 4,
    productNames: categories.map((cat) => {
      const items = byCategory.get(cat).sort((a, b) => b.total_quantity - a.total_quantity);
      return items[i] ? items[i].product_name : "";
    }),
  }));

  new Chart(document.getElementById("chart-top-products-category"), {
    type: "bar",
    data: { labels: categories, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: {
        legend: { display: true, position: "bottom" },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.productNames[ctx.dataIndex]}: ${ctx.formattedValue} qty`,
          },
        },
      },
    },
  });
}

// Q2 — monthly revenue trend (line)
async function renderMonthlyRevenue() {
  const rows = await getJSON("/api/monthly-revenue-trend");
  new Chart(document.getElementById("chart-monthly-revenue"), {
    type: "line",
    data: {
      labels: rows.map((r) => r.month),
      datasets: [{
        label: "Revenue",
        data: rows.map((r) => r.total_revenue),
        borderColor: SERIES[0],
        backgroundColor: SERIES[0],
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.2,
        fill: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: { legend: { display: false } },
    },
  });
}

// Q3 — payment method distribution (pie)
async function renderPaymentDistribution() {
  const rows = await getJSON("/api/payment-method-distribution");
  new Chart(document.getElementById("chart-payment-distribution"), {
    type: "pie",
    data: {
      labels: rows.map((r) => r.payment_method),
      datasets: [{
        data: rows.map((r) => r.pct),
        backgroundColor: SERIES,
        borderColor: color("--surface-1"),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: "bottom" },
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.formattedValue}%` } },
      },
    },
  });
}

// Q4 — revenue per store per month (multi-line)
async function renderRevenueByStore() {
  const rows = await getJSON("/api/revenue-by-store");
  const byStore = groupBy(rows, "store_name");
  const months = [...new Set(rows.map((r) => r.month))].sort();

  const datasets = [...byStore.entries()].map(([store, items], i) => {
    const byMonth = new Map(items.map((r) => [r.month, r.revenue]));
    return {
      label: store,
      data: months.map((m) => byMonth.get(m) || 0),
      borderColor: SERIES[i % SERIES.length],
      backgroundColor: SERIES[i % SERIES.length],
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.2,
      fill: false,
    };
  });

  new Chart(document.getElementById("chart-revenue-store"), {
    type: "line",
    data: { labels: months, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
}

// Q5 — promotion effectiveness: discount per promo (bar) + avg tx value promo vs baseline (bar)
async function renderPromotionEffectiveness() {
  const data = await getJSON("/api/promotion-effectiveness");

  new Chart(document.getElementById("chart-promo-discount"), {
    type: "bar",
    data: {
      labels: data.by_promo.map((r) => r.promo_name),
      datasets: [{
        label: "Total Discount",
        data: data.by_promo.map((r) => r.total_discount),
        backgroundColor: SERIES[1],
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      scales: commonScales(),
      plugins: { legend: { display: false } },
    },
  });

  new Chart(document.getElementById("chart-promo-avg"), {
    type: "bar",
    data: {
      labels: data.promo_vs_baseline.map((r) => r.segment),
      datasets: [{
        label: "Avg Transaction Value",
        data: data.promo_vs_baseline.map((r) => r.avg_transaction_value),
        backgroundColor: [SERIES[0], SERIES[3]],
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: { legend: { display: false } },
    },
  });
}

// Q6 — top products by city (grouped bar)
async function renderTopProductsByCity() {
  const rows = await getJSON("/api/top-products-by-city");
  const byCity = groupBy(rows, "city");
  const cities = [...byCity.keys()];
  const maxN = 3;

  const datasets = Array.from({ length: maxN }, (_, i) => ({
    label: `#${i + 1}`,
    data: cities.map((c) => {
      const items = byCity.get(c).sort((a, b) => b.revenue - a.revenue);
      return items[i] ? items[i].revenue : 0;
    }),
    backgroundColor: SERIES[i % SERIES.length],
    borderRadius: 4,
    productNames: cities.map((c) => {
      const items = byCity.get(c).sort((a, b) => b.revenue - a.revenue);
      return items[i] ? items[i].product_name : "";
    }),
  }));

  new Chart(document.getElementById("chart-top-products-city"), {
    type: "bar",
    data: { labels: cities, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: {
        legend: { display: true, position: "bottom" },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.productNames[ctx.dataIndex]}: Rp ${ctx.formattedValue}`,
          },
        },
      },
    },
  });
}

// Q7 — customer segments (stacked bar per city)
async function renderCustomerSegments() {
  const rows = await getJSON("/api/customer-segments");
  const byCity = groupBy(rows, "city");
  const cities = [...byCity.keys()];
  const segments = ["High", "Medium", "Low"];

  const datasets = segments.map((seg, i) => ({
    label: seg,
    data: cities.map((c) => {
      const found = byCity.get(c).find((r) => r.segment === seg);
      return found ? found.customer_count : 0;
    }),
    backgroundColor: SERIES[i % SERIES.length],
  }));

  new Chart(document.getElementById("chart-customer-segments"), {
    type: "bar",
    data: { labels: cities, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, grid: { color: GRID }, ticks: { color: TEXT_SECONDARY } },
        y: { stacked: true, grid: { color: GRID }, ticks: { color: TEXT_SECONDARY } },
      },
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
}

// Q8 — transactions by day of week (grouped bar: count + revenue)
async function renderTransactionsByDay() {
  const rows = await getJSON("/api/transactions-by-day");
  new Chart(document.getElementById("chart-transactions-day"), {
    type: "bar",
    data: {
      labels: rows.map((r) => r.day_name),
      datasets: [{
        label: "Transaksi",
        data: rows.map((r) => r.transaction_count),
        backgroundColor: SERIES[0],
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: commonScales(),
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => `Revenue: Rp ${rows[ctx.dataIndex].revenue.toLocaleString()}`,
          },
        },
      },
    },
  });
}

Promise.allSettled([
  renderTopProductsByCategory(),
  renderMonthlyRevenue(),
  renderPaymentDistribution(),
  renderRevenueByStore(),
  renderPromotionEffectiveness(),
  renderTopProductsByCity(),
  renderCustomerSegments(),
  renderTransactionsByDay(),
]).then((results) => {
  results.forEach((r) => {
    if (r.status === "rejected") console.error(r.reason);
  });
});
