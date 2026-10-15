/**
 * CPU Scheduler Controller
 */

let lastGanttData = [];
let cpuComparisonChart = null;

// Initial process list
let inputProcesses = [
    { pid: "P1", arrival_time: 0, burst_time: 8, priority: 2 },
    { pid: "P2", arrival_time: 1, burst_time: 4, priority: 1 },
    { pid: "P3", arrival_time: 2, burst_time: 9, priority: 3 },
    { pid: "P4", arrival_time: 3, burst_time: 5, priority: 2 }
];

function renderInputTable() {
    const tbody = document.getElementById("cpu-process-input-body");
    if (!tbody) return;

    tbody.innerHTML = inputProcesses.map((p, idx) => `
        <tr>
            <td><input type="text" class="form-control form-control-sm form-control-custom font-mono" value="${p.pid}" onchange="updateProcessInput(${idx}, 'pid', this.value)"></td>
            <td><input type="number" class="form-control form-control-sm form-control-custom font-mono" value="${p.arrival_time}" min="0" onchange="updateProcessInput(${idx}, 'arrival_time', this.value)"></td>
            <td><input type="number" class="form-control form-control-sm form-control-custom font-mono" value="${p.burst_time}" min="1" onchange="updateProcessInput(${idx}, 'burst_time', this.value)"></td>
            <td><input type="number" class="form-control form-control-sm form-control-custom font-mono" value="${p.priority}" min="1" onchange="updateProcessInput(${idx}, 'priority', this.value)"></td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="removeProcessRow(${idx})">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        </tr>
    `).join("");
}

function updateProcessInput(index, field, val) {
    if (field === 'pid') {
        inputProcesses[index].pid = val.trim();
    } else {
        inputProcesses[index][field] = parseInt(val) || 0;
    }
}

function addProcessRow() {
    const nextNum = inputProcesses.length + 1;
    inputProcesses.push({
        pid: `P${nextNum}`,
        arrival_time: nextNum - 1,
        burst_time: 5,
        priority: 2
    });
    renderInputTable();
}

async function loadActiveProcesses() {
    const res = await apiRequest("/api/process");
    if (!res || !res.success || !res.processes || res.processes.length === 0) {
        showToast("No Processes", "No active processes found to import.", "warning");
        return;
    }

    inputProcesses = res.processes.map(p => ({
        pid: p.pid,
        arrival_time: p.arrival_time,
        burst_time: Math.max(1, p.burst_time),
        priority: p.priority || 1
    }));
    renderInputTable();
    showToast("Imported System Tasks", `Loaded ${inputProcesses.length} processes (including real DFS operations) into CPU queue.`, "success");
    runCpuScheduler();
}

function removeProcessRow(idx) {
    if (inputProcesses.length <= 1) {
        showToast("Error", "Must have at least one process.", "warning");
        return;
    }
    inputProcesses.splice(idx, 1);
    renderInputTable();
}

function toggleQuantumInput() {
    const algo = document.getElementById("select-algorithm").value;
    const container = document.getElementById("quantum-container");
    if (algo === "RR") {
        container.style.display = "block";
    } else {
        container.style.display = "none";
    }
}

const processColors = {
    "P1": "#3b82f6", "P2": "#8b5cf6", "P3": "#10b981",
    "P4": "#f59e0b", "P5": "#06b6d4", "P6": "#ec4899",
    "IDLE": "#334155"
};

function getProcessColor(pid) {
    if (processColors[pid]) return processColors[pid];
    // Dynamic color fallback for new PIDs
    let hash = 0;
    for (let i = 0; i < pid.length; i++) hash = pid.charCodeAt(i) + ((hash << 5) - hash);
    return `hsl(${Math.abs(hash) % 360}, 75%, 55%)`;
}

async function runCpuScheduler() {
    const algorithm = document.getElementById("select-algorithm").value;
    const quantum = parseInt(document.getElementById("input-quantum").value) || 2;

    const res = await apiRequest("/api/cpu/run", "POST", {
        algorithm: algorithm,
        quantum: quantum,
        processes: inputProcesses
    });

    if (!res || !res.success) {
        showToast("Execution Failed", res ? res.message : "Error executing CPU scheduler.", "danger");
        return;
    }

    const result = res.result;
    document.getElementById("gantt-algo-name").textContent = result.algorithm;
    
    // Render Gantt Chart
    renderGanttChart(result.gantt_chart);

    // Update Sequence & Totals
    document.getElementById("execution-sequence-text").textContent = result.execution_order.join(" → ");
    const totalTime = result.gantt_chart.length > 0 ? result.gantt_chart[result.gantt_chart.length - 1].end_time : 0;
    document.getElementById("total-exec-time").textContent = `${totalTime} s`;

    // Render Metrics Table
    renderMetricsTable(result.process_metrics);

    // Render Averages
    document.getElementById("metric-avg-wt").textContent = `${result.averages.avg_waiting_time} s`;
    document.getElementById("metric-avg-tat").textContent = `${result.averages.avg_turnaround_time} s`;
    document.getElementById("metric-avg-rt").textContent = `${result.averages.avg_response_time} s`;

    showToast("CPU Simulation Complete", `Executed ${result.algorithm} algorithm successfully.`, "success");
}

function renderGanttChart(gantt) {
    lastGanttData = gantt;
    const container = document.getElementById("gantt-chart-display");
    if (!container) return;

    if (!gantt || gantt.length === 0) {
        container.innerHTML = '<div class="text-muted small m-auto">No execution timeline data.</div>';
        return;
    }

    const totalDuration = gantt.reduce((acc, item) => acc + item.duration, 0);

    container.innerHTML = gantt.map(item => {
        const widthPercent = Math.max(6, (item.duration / totalDuration) * 100);
        const bg = item.pid === "IDLE" ? "gantt-idle" : "";
        const style = item.pid !== "IDLE" ? `background: ${getProcessColor(item.pid)};` : "";

        return `
            <div class="gantt-block ${bg}" style="flex: ${item.duration}; min-width: 45px; ${style}" title="${item.pid}: ${item.start_time}s - ${item.end_time}s">
                <div>${item.pid}</div>
                <div class="gantt-time">${item.start_time}-${item.end_time}s</div>
            </div>
        `;
    }).join("");
}

function renderMetricsTable(metrics) {
    const tbody = document.getElementById("cpu-metrics-table-body");
    if (!tbody) return;

    tbody.innerHTML = metrics.map(m => `
        <tr>
            <td class="font-mono fw-bold text-primary">${m.pid}</td>
            <td class="font-mono">${m.arrival_time} s</td>
            <td class="font-mono">${m.burst_time} s</td>
            <td class="font-mono">${m.completion_time} s</td>
            <td class="font-mono text-purple fw-bold">${m.turnaround_time} s</td>
            <td class="font-mono text-primary fw-bold">${m.waiting_time} s</td>
            <td class="font-mono text-success fw-bold">${m.response_time} s</td>
        </tr>
    `).join("");
}

function playGanttAnimation() {
    if (!lastGanttData || lastGanttData.length === 0) {
        showToast("Animation", "Run a simulation first.", "warning");
        return;
    }

    const container = document.getElementById("gantt-chart-display");
    container.innerHTML = "";
    let idx = 0;

    const interval = setInterval(() => {
        if (idx >= lastGanttData.length) {
            clearInterval(interval);
            return;
        }

        const item = lastGanttData[idx];
        const bg = item.pid === "IDLE" ? "gantt-idle" : "";
        const style = item.pid !== "IDLE" ? `background: ${getProcessColor(item.pid)};` : "";

        const blockHtml = `
            <div class="gantt-block ${bg}" style="flex: ${item.duration}; min-width: 45px; ${style}">
                <div>${item.pid}</div>
                <div class="gantt-time">${item.start_time}-${item.end_time}s</div>
            </div>
        `;
        container.insertAdjacentHTML("beforeend", blockHtml);
        idx++;
    }, 400);
}

async function compareAllCpuAlgorithms() {
    const quantum = parseInt(document.getElementById("input-quantum").value) || 2;

    const fcfsRes = await apiRequest("/api/cpu/run", "POST", { algorithm: "FCFS", quantum: quantum, processes: inputProcesses });
    const rrRes = await apiRequest("/api/cpu/run", "POST", { algorithm: "RR", quantum: quantum, processes: inputProcesses });
    const prioRes = await apiRequest("/api/cpu/run", "POST", { algorithm: "PRIORITY", quantum: quantum, processes: inputProcesses });
    const sjfRes = await apiRequest("/api/cpu/run", "POST", { algorithm: "SJF", quantum: quantum, processes: inputProcesses });

    const card = document.getElementById("cpu-comparison-card");
    card.style.display = "block";
    card.scrollIntoView({ behavior: "smooth" });

    const labels = ["FCFS", `Round Robin (Q=${quantum})`, "Priority", "SJF"];
    const avgWTs = [
        fcfsRes.result.averages.avg_waiting_time,
        rrRes.result.averages.avg_waiting_time,
        prioRes.result.averages.avg_waiting_time,
        sjfRes.result.averages.avg_waiting_time
    ];
    const avgTATs = [
        fcfsRes.result.averages.avg_turnaround_time,
        rrRes.result.averages.avg_turnaround_time,
        prioRes.result.averages.avg_turnaround_time,
        sjfRes.result.averages.avg_turnaround_time
    ];

    const ctx = document.getElementById("chart-cpu-comparison");
    if (cpuComparisonChart) cpuComparisonChart.destroy();

    cpuComparisonChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Avg Waiting Time (WT)",
                    data: avgWTs,
                    backgroundColor: "rgba(59, 130, 246, 0.75)",
                    borderColor: "#3b82f6",
                    borderWidth: 1
                },
                {
                    label: "Avg Turnaround Time (TAT)",
                    data: avgTATs,
                    backgroundColor: "rgba(139, 92, 246, 0.75)",
                    borderColor: "#8b5cf6",
                    borderWidth: 1
                }
            ]
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

    showToast("Comparison Loaded", "Compared FCFS, RR, Priority, and SJF side-by-side.", "info");
}

document.addEventListener("DOMContentLoaded", () => {
    renderInputTable();
    runCpuScheduler();
});
