const BASE = "";

async function fetchJSON(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

let charts = {};

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function renderBarChart(canvasId, labels, data, label, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext("2d");
  charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label, data, backgroundColor: color, borderRadius: 4 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function renderGroupedBarChart(canvasId, labels, presentData, absentData) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext("2d");
  charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Presente", data: presentData, backgroundColor: "#4ade80", borderRadius: 4 },
        { label: "Ausente",  data: absentData,  backgroundColor: "#f87171", borderRadius: 4 },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function getFilters() {
  return {
    groupId: document.getElementById("group-filter").value,
    dateFrom: document.getElementById("date-from").value,
    dateTo: document.getElementById("date-to").value,
    personName: document.getElementById("person-name").value,
  };
}

async function loadDashboard(filters = {}) {
  const params = new URLSearchParams();
  if (filters.groupId && filters.groupId !== "all") params.set("group_id", filters.groupId);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.personName && filters.personName.trim()) params.set("person_name", filters.personName.trim());
  const qs = params.toString() ? `?${params.toString()}` : "";

  try {
    const [absent, byWeek, present] = await Promise.all([
      fetchJSON(`/api/top-absent${qs}`),
      fetchJSON(`/api/attendance-by-week${qs}`),
      fetchJSON(`/api/top-present${qs}`),
    ]);

    renderBarChart(
      "topAbsentChart",
      absent.map(r => r.name),
      absent.map(r => r.absences),
      "Ausências",
      "#f87171"
    );

    renderGroupedBarChart(
      "attendanceByWeekChart",
      byWeek.map(r => `Sem ${r.week}`),
      byWeek.map(r => r.present),
      byWeek.map(r => r.absent)
    );

    renderBarChart(
      "topPresentChart",
      present.map(r => r.name),
      present.map(r => r.presences),
      "Presenças",
      "#4ade80"
    );
  } catch (err) {
    console.error("Erro ao carregar dashboard:", err);
  }
}

async function loadGroups() {
  const select = document.getElementById("group-filter");
  try {
    const groups = await fetchJSON("/api/groups");
    groups.forEach(g => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = g.name;
      select.appendChild(opt);
    });
  } catch (err) {
    console.warn("Não foi possível carregar grupos:", err);
  }
  select.addEventListener("change", () => loadDashboard(getFilters()));
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadGroups();
  document.getElementById("apply-filters").addEventListener("click", () => loadDashboard(getFilters()));
  loadDashboard(getFilters());
});
