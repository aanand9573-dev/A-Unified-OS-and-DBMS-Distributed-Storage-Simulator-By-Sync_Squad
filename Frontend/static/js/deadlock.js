/**
 * Deadlock Management Controller
 */

let deadlockData = null;

async function calculateDeadlockSafety() {
    const res = await apiRequest("/api/deadlock/calculate");
    if (!res || !res.success) return;

    deadlockData = res.result;

    // Update Status Header Card
    const titleEl = document.getElementById("deadlock-status-title");
    const descEl = document.getElementById("deadlock-status-desc");
    const iconEl = document.getElementById("deadlock-status-icon");

    if (deadlockData.is_safe) {
        titleEl.textContent = "SYSTEM IN SAFE STATE";
        titleEl.className = "fw-bold mb-1 text-success";
        iconEl.className = "kpi-icon kpi-green";
        const seq = deadlockData.safe_sequence.join(" → ");
        document.getElementById("deadlock-safe-seq-text").textContent = `< ${seq} >`;
        descEl.innerHTML = `Safe Sequence Found: <span class="font-mono text-white fw-bold">&lt;${seq}&gt;</span>`;
    } else {
        titleEl.textContent = "UNSAFE STATE / DEADLOCK DETECTED";
        titleEl.className = "fw-bold mb-1 text-danger";
        iconEl.className = "kpi-icon kpi-warning";
        const procs = (deadlockData.deadlocked_processes || []).join(", ");
        descEl.innerHTML = `<span class="text-danger fw-bold">Warning: Deadlocked candidate processes: [${procs}]</span>`;
    }

    // Render Available Vector Inputs
    renderAvailableVector(deadlockData.available, deadlockData.resource_names);

    // Render Allocation Table
    renderMatrixTable("alloc", deadlockData.allocation, deadlockData.process_names, deadlockData.resource_names);

    // Render Max Table
    renderMatrixTable("max", deadlockData.max_matrix, deadlockData.process_names, deadlockData.resource_names);

    // Render Need Table
    renderMatrixTable("need", deadlockData.need_matrix, deadlockData.process_names, deadlockData.resource_names, true);

    // Render Execution Steps
    renderExecutionSteps(deadlockData.execution_steps);

    // Populate modal process select
    populateRequestModal(deadlockData.process_names, deadlockData.resource_names);
}

function renderAvailableVector(avail, resNames) {
    const container = document.getElementById("available-inputs-container");
    if (!container) return;

    container.innerHTML = avail.map((val, idx) => `
        <div class="input-group input-group-sm">
            <span class="input-group-text bg-dark border-secondary text-primary font-mono fw-bold">${resNames[idx] || 'R' + idx}</span>
            <input type="number" class="form-control form-control-custom font-mono" value="${val}" min="0" onchange="updateAvailableVal(${idx}, this.value)">
        </div>
    `).join("");
}

function updateAvailableVal(idx, val) {
    deadlockData.available[idx] = parseInt(val) || 0;
    saveMatricesToServer();
}

function renderMatrixTable(prefix, matrix, procNames, resNames, readOnly = false) {
    const headRow = document.getElementById(`${prefix}-table-head`);
    const tbody = document.getElementById(`${prefix}-table-body`);
    if (!headRow || !tbody) return;

    headRow.innerHTML = `<th>Process</th>` + resNames.map(r => `<th>${r}</th>`).join("");

    tbody.innerHTML = matrix.map((row, pIdx) => `
        <tr>
            <td class="font-mono fw-bold text-primary">${procNames[pIdx]}</td>
            ${row.map((val, rIdx) => `
                <td>
                    ${readOnly ? 
                        `<span class="font-mono text-purple fw-bold">${val}</span>` : 
                        `<input type="number" class="form-control form-control-sm form-control-custom font-mono" value="${val}" min="0" onchange="updateMatrixCell('${prefix}', ${pIdx}, ${rIdx}, this.value)">`}
                </td>
            `).join("")}
        </tr>
    `).join("");
}

function updateMatrixCell(prefix, pIdx, rIdx, val) {
    const num = parseInt(val) || 0;
    if (prefix === "alloc") {
        deadlockData.allocation[pIdx][rIdx] = num;
    } else if (prefix === "max") {
        deadlockData.max_matrix[pIdx][rIdx] = num;
    }
    saveMatricesToServer();
}

async function saveMatricesToServer() {
    await apiRequest("/api/deadlock/calculate", "POST", {
        process_names: deadlockData.process_names,
        resource_names: deadlockData.resource_names,
        available: deadlockData.available,
        allocation: deadlockData.allocation,
        max_matrix: deadlockData.max_matrix
    });
    calculateDeadlockSafety();
}

function renderExecutionSteps(steps) {
    const tbody = document.getElementById("bankers-steps-body");
    if (!tbody) return;

    if (!steps || steps.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">No safe execution sequence possible. Deadlock present!</td></tr>';
        return;
    }

    tbody.innerHTML = steps.map(s => `
        <tr>
            <td class="font-mono fw-bold">Step ${s.step}</td>
            <td class="fw-bold text-success font-mono">${s.process}</td>
            <td class="font-mono text-secondary">[${s.prev_work.join(", ")}]</td>
            <td class="font-mono text-warning">[${s.need.join(", ")}]</td>
            <td class="font-mono text-primary">[${s.allocation.join(", ")}]</td>
            <td class="font-mono text-success fw-bold">[${s.new_work.join(", ")}]</td>
        </tr>
    `).join("");
}

function populateRequestModal(procNames, resNames) {
    const select = document.getElementById("req-select-pid");
    if (select) {
        select.innerHTML = procNames.map(p => `<option value="${p}">${p}</option>`).join("");
    }

    const container = document.getElementById("req-inputs-container");
    if (container) {
        container.innerHTML = resNames.map((r, idx) => `
            <div class="input-group input-group-sm">
                <span class="input-group-text bg-dark border-secondary text-secondary font-mono">${r}</span>
                <input type="number" class="form-control form-control-custom font-mono req-res-val" value="0" min="0">
            </div>
        `).join("");
    }
}

function openRequestModal() {
    const modal = new bootstrap.Modal(document.getElementById("requestResourceModal"));
    modal.show();
}

async function resetDeadlock() {
    const res = await apiRequest("/api/deadlock/reset", "POST");
    if (res.success) {
        showToast("Deadlock Reset", "Matrices reset to sample configuration.", "info");
        calculateDeadlockSafety();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    calculateDeadlockSafety();

    const form = document.getElementById("form-resource-request");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const pid = document.getElementById("req-select-pid").value;
            const inputEls = document.querySelectorAll(".req-res-val");
            const reqVec = Array.from(inputEls).map(el => parseInt(el.value) || 0);

            const res = await apiRequest("/api/deadlock/request", "POST", {
                pid: pid,
                request_vector: reqVec
            });

            if (res.success && res.result.granted) {
                showToast("Request Granted", res.result.message, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("requestResourceModal"));
                if (modal) modal.hide();
                calculateDeadlockSafety();
            } else {
                showToast("Request Denied", res.result ? res.result.message : "Request failed.", "danger");
            }
        });
    }
});
