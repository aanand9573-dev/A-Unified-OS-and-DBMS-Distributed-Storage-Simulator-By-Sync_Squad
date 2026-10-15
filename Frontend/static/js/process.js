/**
 * Process Management Controller
 */

async function loadProcesses() {
    const data = await apiRequest("/api/process");
    if (!data || !data.success) return;

    const procs = data.processes;
    const summary = data.summary;

    // Update Summary Header
    document.getElementById("summary-running").textContent = summary.running_process ? `${summary.running_process.pid} (${summary.running_process.name})` : "IDLE";
    document.getElementById("summary-ready-count").textContent = `${summary.ready} Processes`;
    document.getElementById("summary-waiting-count").textContent = `${summary.waiting} Process${summary.waiting !== 1 ? 'es' : ''}`;
    document.getElementById("summary-terminated-count").textContent = `${summary.terminated} Process${summary.terminated !== 1 ? 'es' : ''}`;

    // Render Table
    const tbody = document.getElementById("process-table-body");
    if (procs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No processes in system. Click "Create Process" to add one.</td></tr>';
        return;
    }

    tbody.innerHTML = procs.map(p => {
        const stateClass = `badge-${p.state.toLowerCase()}`;
        return `
            <tr>
                <td class="font-mono fw-bold text-primary">${p.pid}</td>
                <td>
                    <div class="fw-bold">${p.name}</div>
                    ${p.details ? `<small class="text-secondary font-mono" style="font-size: 0.725rem;">${p.details}</small>` : ''}
                </td>
                <td><span class="badge bg-secondary-subtle text-light">${p.process_type}</span></td>
                <td class="font-mono">${p.arrival_time} s</td>
                <td class="font-mono">${p.burst_time} s</td>
                <td class="font-mono"><span class="badge bg-purple-subtle text-purple">Prio ${p.priority}</span></td>
                <td><span class="badge badge-state ${stateClass}">${p.state}</span></td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-custom dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            State Actions
                        </button>
                        <ul class="dropdown-menu dropdown-menu-dark">
                            <li><a class="dropdown-item" href="#" onclick="changeState('${p.pid}', 'READY')"><i class="fas fa-play text-primary me-2"></i>Move to READY</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeState('${p.pid}', 'RUNNING')"><i class="fas fa-microchip text-success me-2"></i>Schedule (RUNNING)</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeState('${p.pid}', 'WAITING')"><i class="fas fa-pause text-warning me-2"></i>I/O Wait (WAITING)</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeState('${p.pid}', 'TERMINATED')"><i class="fas fa-stop text-danger me-2"></i>Terminate</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteProcess('${p.pid}')"><i class="fas fa-trash me-2"></i>Delete PCB</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

async function changeState(pid, newState) {
    const res = await apiRequest("/api/process/transition", "POST", { pid: pid, state: newState });
    if (res.success) {
        showToast("State Transition", `Process ${pid} is now in ${newState} state.`, "success");
        loadProcesses();
    } else {
        showToast("Transition Failed", res.message, "danger");
    }
}

async function deleteProcess(pid) {
    if (confirm(`Delete process PCB ${pid}?`)) {
        const res = await apiRequest("/api/process", "DELETE", { pid: pid });
        if (res.success) {
            showToast("Process Deleted", `PCB for ${pid} removed.`, "warning");
            loadProcesses();
        }
    }
}

async function resetProcesses() {
    const res = await apiRequest("/api/process/reset", "POST");
    if (res.success) {
        showToast("Reset Completed", "Sample processes restored.", "info");
        loadProcesses();
    }
}

async function loadProcessHistory() {
    const res = await apiRequest("/api/process/history");
    if (!res || !res.success) return;

    const tbody = document.getElementById("process-history-body");
    if (!tbody) return;

    if (!res.history || res.history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No process event history recorded yet.</td></tr>';
        return;
    }

    tbody.innerHTML = res.history.map(h => `
        <tr>
            <td class="font-mono small text-secondary">${h.timestamp}</td>
            <td class="font-mono fw-bold text-primary">${h.pid}</td>
            <td class="fw-bold">${h.name}</td>
            <td><span class="badge bg-secondary-subtle text-light">${h.process_type}</span></td>
            <td><span class="badge bg-dark border border-secondary text-info font-mono">${h.action}</span></td>
            <td class="small text-muted font-mono">${h.details || '--'}</td>
        </tr>
    `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
    loadProcesses();
    loadProcessHistory();

    const form = document.getElementById("form-create-process");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const pid = document.getElementById("input-pid").value.trim();
            const name = document.getElementById("input-name").value.trim();
            const ptype = document.getElementById("input-type").value;
            const state = document.getElementById("input-state").value;
            const at = parseInt(document.getElementById("input-at").value);
            const bt = parseInt(document.getElementById("input-bt").value);
            const priority = parseInt(document.getElementById("input-priority").value);

            const res = await apiRequest("/api/process", "POST", {
                pid: pid,
                name: name,
                process_type: ptype,
                state: state,
                arrival_time: at,
                burst_time: bt,
                priority: priority
            });

            if (res.success) {
                showToast("Process Created", `Process ${pid} (${name}) added to system.`, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("createProcessModal"));
                if (modal) modal.hide();
                form.reset();
                loadProcesses();
                loadProcessHistory();
            } else {
                showToast("Creation Failed", res.message, "danger");
            }
        });
    }
});
