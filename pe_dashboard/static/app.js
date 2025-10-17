const DEFAULT_TICKERS = ["NVDA", "MSFT", "GOOG", "AMZN", "META", "AVGO", "ORCL", "TLSA", "AAPL"];
const COLOR_PALETTE = [
  "#2563eb",
  "#16a34a",
  "#d946ef",
  "#f97316",
  "#facc15",
  "#06b6d4",
  "#f43f5e",
  "#8b5cf6",
  "#10b981",
];
const API_ROOT = "/api/pe";

const state = {
  selectedTickers: new Set(DEFAULT_TICKERS),
  mode: "combined",
  startDate: null,
  endDate: null,
  combinedChart: null,
  individualCharts: new Map(),
};

function formatDate(date) {
  return date.toISOString().slice(0, 10);
}

function initDateInputs() {
  const startInput = document.getElementById("start-date");
  const endInput = document.getElementById("end-date");
  const today = new Date();
  const defaultStart = new Date();
  defaultStart.setFullYear(today.getFullYear() - 25);

  startInput.value = formatDate(defaultStart);
  endInput.value = formatDate(today);

  state.startDate = startInput.value;
  state.endDate = endInput.value;

  startInput.addEventListener("change", (event) => {
    state.startDate = event.target.value;
  });
  endInput.addEventListener("change", (event) => {
    state.endDate = event.target.value;
  });
}

function initTickerCheckboxes() {
  const container = document.getElementById("ticker-checkboxes");
  DEFAULT_TICKERS.forEach((ticker) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "ticker";
    checkbox.value = ticker;
    checkbox.checked = state.selectedTickers.has(ticker);
    checkbox.addEventListener("change", (event) => {
      if (event.target.checked) {
        state.selectedTickers.add(ticker);
      } else {
        state.selectedTickers.delete(ticker);
      }
    });

    label.appendChild(checkbox);
    label.append(ticker);
    container.appendChild(label);
  });
}

function initModeSwitch() {
  const form = document.getElementById("control-form");
  form.addEventListener("change", (event) => {
    if (event.target.name === "mode") {
      state.mode = event.target.value;
      renderMode();
    }
  });
}

function renderMode() {
  const combined = document.getElementById("combined-chart-container");
  const individual = document.getElementById("individual-charts");

  if (state.mode === "combined") {
    combined.style.display = "block";
    individual.style.display = "none";
  } else {
    combined.style.display = "none";
    individual.style.display = "grid";
  }
}

async function fetchPeData() {
  if (state.selectedTickers.size === 0) {
    throw new Error("Please select at least one company.");
  }

  const params = new URLSearchParams({
    tickers: Array.from(state.selectedTickers).join(","),
    start: state.startDate,
    end: state.endDate,
  });

  const response = await fetch(`${API_ROOT}?${params.toString()}`);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message = errorBody?.detail ?? response.statusText;
    throw new Error(message || "Failed to fetch P/E data");
  }

  return response.json();
}

function buildCombinedChart(canvas, data) {
  const labels = extractLabels(data);
  const datasets = Object.entries(data).map(([ticker, values], index) => {
    const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
    return {
      label: ticker,
      data: alignSeries(labels, values),
      borderWidth: 2,
      tension: 0.25,
      borderColor: color,
      backgroundColor: `${color}33`,
      spanGaps: true,
    };
  });

  if (state.combinedChart) {
    state.combinedChart.destroy();
  }

  state.combinedChart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { title: { display: true, text: "P/E" } },
        x: { title: { display: true, text: "Date" } },
      },
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}`,
          },
        },
      },
    },
  });
}

function buildIndividualCharts(container, data) {
  // Destroy existing charts
  state.individualCharts.forEach((chart) => chart.destroy());
  state.individualCharts.clear();
  container.replaceChildren();

  Object.entries(data).forEach(([ticker, values], index) => {
    const wrapper = document.createElement("div");
    wrapper.className = "individual-chart";

    const title = document.createElement("h3");
    title.textContent = ticker;

    const canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", `${ticker} P/E chart`);

    wrapper.appendChild(title);
    wrapper.appendChild(canvas);
    container.appendChild(wrapper);

    const labels = values.map((item) => item.date);
    const dataset = values.map((item) => item.pe);

    const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: ticker,
            data: dataset,
            borderWidth: 2,
            tension: 0.25,
            borderColor: color,
            backgroundColor: `${color}33`,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { title: { display: true, text: "P/E" } },
          x: { title: { display: true, text: "Date" } },
        },
      },
    });

    state.individualCharts.set(ticker, chart);
  });
}

function extractLabels(data) {
  const labelSet = new Set();
  Object.values(data).forEach((series) => {
    series.forEach((point) => labelSet.add(point.date));
  });
  return Array.from(labelSet).sort();
}

function alignSeries(labels, series) {
  const lookup = new Map(series.map((item) => [item.date, item.pe]));
  return labels.map((label) => lookup.get(label) ?? null);
}

function displayError(message) {
  const combinedContainer = document.getElementById("combined-chart-container");
  const individualContainer = document.getElementById("individual-charts");

  combinedContainer.innerHTML = `<canvas id="combined-chart" aria-label="Combined P/E chart" role="img"></canvas>`;
  individualContainer.replaceChildren();

  const target = state.mode === "combined" ? combinedContainer : individualContainer;
  const errorElement = document.createElement("div");
  errorElement.className = "error";
  errorElement.textContent = message;
  target.appendChild(errorElement);

  if (state.combinedChart) {
    state.combinedChart.destroy();
    state.combinedChart = null;
  }
  state.individualCharts.forEach((chart) => chart.destroy());
  state.individualCharts.clear();
}

async function handleSubmit(event) {
  event.preventDefault();
  const combinedCanvas = document.getElementById("combined-chart");
  const individualContainer = document.getElementById("individual-charts");

  try {
    const data = await fetchPeData();
    if (state.mode === "combined") {
      buildCombinedChart(combinedCanvas, data);
    } else {
      buildIndividualCharts(individualContainer, data);
    }
  } catch (error) {
    console.error(error);
    displayError(error.message);
  }
}

function init() {
  initTickerCheckboxes();
  initDateInputs();
  initModeSwitch();
  renderMode();
  document.getElementById("control-form").addEventListener("submit", handleSubmit);
  // Load initial data
  document.getElementById("control-form").dispatchEvent(new Event("submit"));
}

window.addEventListener("DOMContentLoaded", init);
