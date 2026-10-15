/**
 * Dashboard Controller
 * Updates summary KPIs, storage nodes, and Chart.js charts.
 */

let processStateChart = null;
let memoryDonutChart = null;

async function loadDashboardData() {
    const data = await apiRequest("/api/dashboard/summary");
    if (!data || !data.success) return;

    // 1. Update DFS KPIs
    const dfs = data.dfs;
    document.getElementById("kpi-dfs-files").textContent = dfs.total_files || 0;
    document.getElementById("kpi-dfs-blocks").textContent = dfs.total_blocks || 0;
    document.getElementById("kpi-online-nodes").textContent = `${dfs.online_nodes} / ${dfs.total_nodes}`;

    // Render DFS Nodes Grid
    renderDashNodes(dfs.nodes);

    // 2. Update OS KPIs
    const proc = data.processes;
    document.getElementById("kpi-total-processes").textContent = proc.total || 0;
    
    const mem = data.memory;
    document.getElementById("kpi-memory-used").textContent = `${mem.used_memory} MB`;
    document.getElementById("badge-frag-percent").textContent = `Ext Frag: ${mem.external_fragmentation} MB`;

    const disk = data.disk;
    if (disk) {
        const headEl = document.getElementById("dash-head-pos");
        if (headEl) headEl.textContent = disk.initial_head !== undefined ? disk.initial_head : 50;

        const algoEl = document.getElementById("dash-disk-algo");
        if (algoEl) algoEl.textContent = disk.active_algorithm || "FCFS";

        const queueEl = document.getElementById("dash-disk-queue");
        if (queueEl) {
            const reqs = disk.requests || [];
            queueEl.textContent = reqs.length > 0 ? `[${reqs.slice(0, 5).join(", ")}${reqs.length > 5 ? '...' : ''}]` : "[]";
        }
    }

    const deadlock = data.deadlock;
    const dlStatusEl = document.getElementById("kpi-deadlock-status");
    const dlIconEl = document.getElementById("kpi-deadlock-icon");
    if (deadlock.is_safe) {
        dlStatusEl.textContent = "SAFE";
        dlStatusEl.className = "kpi-value fs-6 text-success";
        dlIconEl.className = "kpi-icon kpi-green";
    } else {
        dlStatusEl.textContent = "DEADLOCK";
        dlStatusEl.className = "kpi-value fs-6 text-danger";
        dlIconEl.className = "kpi-icon kpi-warning";
    }

    // Mutex status
    const mutex = data.synchronization.mutex;
    const mutexOwnerEl = document.getElementById("dash-mutex-owner");
    const mutexBadgeEl = document.getElementById("dash-mutex-badge");
    if (mutex.is_locked) {
        mutexOwnerEl.textContent = `Owner: ${mutex.owner_pid} (LOCKED)`;
        mutexBadgeEl.textContent = "LOCKED";
        mutexBadgeEl.className = "badge badge-running";
    } else {
        mutexOwnerEl.textContent = "UNLOCKED (Available)";
        mutexBadgeEl.textContent = "UNLOCKED";
        mutexBadgeEl.className = "badge badge-ready";
    }

    document.getElementById("dash-ready-count").textContent = proc.ready || 0;

    // 3. Render Process State Chart
    renderProcessChart(proc.state_counts);

    // 4. Render Memory Utilization Donut Chart
    renderMemoryChart(mem.used_memory, mem.free_memory);

    // 5. Render Live System Activity Logs
    renderLogs(data.recent_logs);
}

function renderDashNodes(nodes) {
    const container = document.getElementById("dash-nodes-row");
    if (!container || !nodes) return;

    container.innerHTML = nodes.map(n => {
        const isOnline = n.status === "ONLINE";
        const percent = Math.min(100, Math.round((n.used_mb / n.capacity_mb) * 100));

        return `
            <div class="col-xl-3 col-md-6">
                <div class="p-3 border ${isOnline ? 'border-secondary-subtle' : 'border-danger'} rounded-3 bg-dark-subtle">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <div class="fw-bold text-white fs-6">${n.name}</div>
                        <span class="badge ${isOnline ? 'badge-running' : 'badge-terminated'}">${n.status}</span>
                    </div>
                    <div class="small text-secondary mb-1">${n.used_mb} MB / ${n.capacity_mb} MB (${percent}%)</div>
                    <div class="progress" style="height: 5px; background: rgba(255,255,255,0.05);">
                        <div class="progress-bar ${isOnline ? 'bg-primary' : 'bg-danger'}" style="width: ${percent}%"></div>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function renderProcessChart(counts) {
    const ctx = document.getElementById("chart-process-states");
    if (!ctx) return;

    const labels = ["NEW", "READY", "RUNNING", "WAITING", "TERMINATED"];
    const values = labels.map(l => counts[l] || 0);

    if (processStateChart) {
        processStateChart.data.datasets[0].data = values;
        processStateChart.update();
        return;
    }

    processStateChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Processes",
                data: values,
                backgroundColor: [
                    "rgba(148, 163, 184, 0.7)",
                    "rgba(59, 130, 246, 0.7)",
                    "rgba(16, 185, 129, 0.85)",
                    "rgba(245, 158, 11, 0.7)",
                    "rgba(239, 68, 68, 0.7)"
                ],
                borderColor: [
                    "#94a3b8",
                    "#3b82f6",
                    "#10b981",
                    "#f59e0b",
                    "#ef4444"
                ],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: "#94a3b8" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderMemoryChart(used, free) {
    const ctx = document.getElementById("chart-memory-usage");
    if (!ctx) return;

    if (memoryDonutChart) {
        memoryDonutChart.data.datasets[0].data = [used, free];
        memoryDonutChart.update();
        return;
    }

    memoryDonutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Used Memory (MB)", "Free Memory (MB)"],
            datasets: [{
                data: [used, free],
                backgroundColor: ["#3b82f6", "#1e293b"],
                borderColor: ["#3b82f6", "#2a364f"],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#f8fafc", font: { family: "Outfit" } }
                }
            }
        }
    });
}

function renderLogs(logs) {
    const container = document.getElementById("dash-terminal-logs");
    if (!container) return;

    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="text-muted small">No recent logs recorded.</div>';
        return;
    }

    container.innerHTML = logs.map(l => `
        <div class="log-entry">
            <span class="log-timestamp">${l.timestamp}</span>
            <span class="log-module log-mod-${l.module.toLowerCase()}">${l.module}</span>
            <span class="log-msg-${l.level.toLowerCase()}">${l.message}</span>
        </div>
    `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
    loadDashboardData();
    setInterval(loadDashboardData, 4000);
});
