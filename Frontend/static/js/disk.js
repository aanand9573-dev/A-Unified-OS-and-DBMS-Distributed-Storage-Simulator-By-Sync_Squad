/**
 * Disk Scheduler Controller
 */

let diskTrackChart = null;
let diskComparisonChart = null;

async function runDiskScheduler() {
    const head = parseInt(document.getElementById("disk-input-head").value) || 50;
    const queueStr = document.getElementById("disk-input-queue").value;
    const algo = document.getElementById("disk-select-algo").value;
    const direction = document.getElementById("disk-select-direction").value;

    const res = await apiRequest("/api/disk/run", "POST", {
        algorithm: algo,
        initial_head: head,
        requests: queueStr,
        direction: direction,
        disk_size: 200
    });

    if (!res || !res.success) {
        showToast("Execution Failed", res ? res.message : "Error executing disk algorithm.", "danger");
        return;
    }

    const r = res.result;
    document.getElementById("disk-active-algo-name").textContent = r.algorithm;
    document.getElementById("disk-sequence-display").textContent = r.scheduled_sequence.join(" → ");
    document.getElementById("disk-total-movement").textContent = `${r.total_movement} Cylinders`;
    document.getElementById("disk-avg-movement").textContent = `${r.avg_movement} Cylinders`;

    // Render Track Line Chart
    renderDiskTrackChart(r.scheduled_sequence, r.algorithm);

    showToast("Disk Simulation Complete", `Executed ${r.algorithm}. Total seek distance: ${r.total_movement} cylinders.`, "success");
}

function renderDiskTrackChart(sequence, algoName) {
    const ctx = document.getElementById("chart-disk-track");
    if (!ctx) return;

    const labels = sequence.map((_, i) => i === 0 ? "Initial (Head)" : `Step ${i}`);

    if (diskTrackChart) diskTrackChart.destroy();

    diskTrackChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: `Head Track Position (${algoName})`,
                data: sequence,
                borderColor: "#3b82f6",
                backgroundColor: "rgba(59, 130, 246, 0.15)",
                fill: true,
                tension: 0.2,
                pointBackgroundColor: "#10b981",
                pointRadius: 6,
                pointHoverRadius: 9
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 200,
                    title: { display: true, text: "Cylinder Track Number (0 - 199)", color: "#94a3b8" },
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                x: {
                    title: { display: true, text: "Sequence Step Order", color: "#94a3b8" },
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            return `Cylinder Track: ${ctx.raw}`;
                        }
                    }
                }
            }
        }
    });
}

async function compareDiskAlgorithms() {
    const head = parseInt(document.getElementById("disk-input-head").value) || 50;
    const queueStr = document.getElementById("disk-input-queue").value;
    const direction = document.getElementById("disk-select-direction").value;

    const res = await apiRequest("/api/disk/compare", "POST", {
        initial_head: head,
        requests: queueStr,
        direction: direction,
        disk_size: 200
    });

    if (!res || !res.success) return;

    const r = res.result;

    const card = document.getElementById("disk-comparison-card");
    card.style.display = "block";
    card.scrollIntoView({ behavior: "smooth" });

    document.getElementById("badge-best-disk-algo").textContent = `Best: ${r.best_algorithm}`;

    // Render Table
    const tbody = document.getElementById("disk-comparison-table-body");
    tbody.innerHTML = r.comparison.map(c => `
        <tr class="${c.algorithm === r.best_algorithm ? 'table-success-subtle fw-bold' : ''}">
            <td class="fw-bold">${c.algorithm} ${c.algorithm === r.best_algorithm ? '<span class="badge bg-success ms-1">EFFICIENT</span>' : ''}</td>
            <td class="font-mono text-primary">${c.total_movement} Cylinders</td>
            <td class="font-mono text-purple">${c.avg_movement} Cylinders</td>
        </tr>
    `).join("");

    // Render Bar Chart
    const ctx = document.getElementById("chart-disk-comparison");
    if (diskComparisonChart) diskComparisonChart.destroy();

    const algos = r.comparison.map(c => c.algorithm);
    const totals = r.comparison.map(c => c.total_movement);

    diskComparisonChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: algos,
            datasets: [{
                label: "Total Head Seek Movement",
                data: totals,
                backgroundColor: ["rgba(59, 130, 246, 0.75)", "rgba(16, 185, 129, 0.75)", "rgba(245, 158, 11, 0.75)"],
                borderColor: ["#3b82f6", "#10b981", "#f59e0b"],
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { display: false }
                }
            }
        }
    });

    showToast("Disk Comparison Complete", `Best disk scheduling algorithm is ${r.best_algorithm}.`, "info");
}

async function loadLiveDiskMetrics() {
    const res = await apiRequest("/api/disk/live_metrics");
    if (!res || !res.success || !res.live) return;

    const live = res.live;
    const selectEl = document.getElementById("live-disk-select-algo");
    if (selectEl) selectEl.value = live.active_algorithm;

    const headEl = document.getElementById("live-disk-head");
    if (headEl) headEl.textContent = live.current_head;

    const servEl = document.getElementById("live-disk-serviced");
    if (servEl) servEl.textContent = live.total_requests_serviced;

    const seeksEl = document.getElementById("live-disk-total-seeks");
    if (seeksEl) seeksEl.textContent = `${live.total_seek_cylinders} Cyl`;

    const avgEl = document.getElementById("live-disk-avg-seek");
    if (avgEl) avgEl.textContent = `${live.avg_seek_cylinders} Cyl`;

    const tbody = document.getElementById("live-disk-tbody");
    if (tbody) {
        if (!live.recent_history || live.recent_history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">No storage I/O operations recorded yet. Upload or download files to generate live disk operations.</td></tr>';
        } else {
            tbody.innerHTML = live.recent_history.slice(0, 15).map(ev => {
                const isSuccess = ev.physical_operation && ev.physical_operation.status === "SUCCESS";
                const sim = ev.simulated_metrics || {};
                const phys = ev.physical_operation || {};
                return `
                    <tr>
                        <td class="font-mono text-primary fw-bold">${ev.id}</td>
                        <td class="small text-secondary font-mono">${ev.timestamp}</td>
                        <td class="font-mono fw-bold">${ev.block_id}</td>
                        <td><span class="badge ${ev.op_type === 'WRITE' ? 'bg-primary-subtle text-primary' : 'bg-success-subtle text-success'}">${ev.op_type}</span></td>
                        <td class="font-mono text-warning fw-bold">Track ${sim.target_cylinder !== undefined ? sim.target_cylinder : '--'}</td>
                        <td class="font-mono">${sim.seek_distance_cylinders !== undefined ? sim.seek_distance_cylinders + ' Cyl' : '--'}</td>
                        <td class="font-mono small text-purple">${phys.host_latency_ms !== undefined ? phys.host_latency_ms + ' ms' : '--'}</td>
                        <td><span class="badge ${isSuccess ? 'badge-running' : 'badge-terminated'}">${phys.status || 'DONE'}</span></td>
                    </tr>
                `;
            }).join("");
        }
    }
}

async function updateLiveDiskAlgorithm(algo) {
    const res = await apiRequest("/api/disk/algorithm", "POST", { algorithm: algo });
    if (res && res.success) {
        showToast("Disk Scheduler Updated", res.message, "info");
        loadLiveDiskMetrics();
    } else {
        showToast("Update Failed", res ? res.message : "Error", "danger");
    }
}

async function loadDfsDiskRequests() {
    const res = await apiRequest("/api/disk/live_metrics");
    if (!res || !res.success) {
        showToast("Error", "Could not load DFS disk requests.", "danger");
        return;
    }
    let reqs = res.dfs_block_tracks || [];
    if (reqs.length === 0 && res.live && res.live.recent_history && res.live.recent_history.length > 0) {
        reqs = res.live.recent_history.map(ev => ev.simulated_metrics ? ev.simulated_metrics.target_cylinder : 50);
    }
    if (reqs.length === 0) {
        reqs = [10, 90, 35, 70, 20];
        showToast("Default Tracks", "No blocks stored in DFS yet. Loaded standard tracks.", "info");
    } else {
        showToast("DFS Tracks Loaded", `Imported ${reqs.length} disk track requests from DFS operations.`, "success");
    }
    document.getElementById("disk-input-queue").value = reqs.join(", ");
    runDiskScheduler();
}

document.addEventListener("DOMContentLoaded", () => {
    runDiskScheduler();
    loadLiveDiskMetrics();
});
