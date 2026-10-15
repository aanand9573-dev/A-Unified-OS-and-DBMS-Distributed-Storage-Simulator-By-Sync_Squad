/**
 * Process Synchronization Controller
 */

async function loadSyncState() {
    const res = await apiRequest("/api/sync/state");
    if (!res || !res.success) return;

    renderMutexState(res.mutex);
    renderSemaphoreState(res.semaphore);
}

function renderMutexState(m) {
    const lockBadge = document.getElementById("mutex-lock-badge");
    const ownerEl = document.getElementById("mutex-current-owner");
    const statusText = document.getElementById("mutex-status-text");
    const queueContainer = document.getElementById("mutex-waiting-queue");
    const historyContainer = document.getElementById("mutex-history-container");

    if (m.is_locked) {
        lockBadge.textContent = "LOCKED";
        lockBadge.className = "badge badge-running";
        ownerEl.textContent = `${m.owner_pid} (IN CRITICAL SECTION)`;
        ownerEl.className = "p-3 border border-success rounded-3 bg-success-subtle text-success font-mono fw-bold fs-4";
        statusText.textContent = `Process ${m.owner_pid} currently holds the lock on ${m.resource_name}.`;
    } else {
        lockBadge.textContent = "UNLOCKED";
        lockBadge.className = "badge badge-ready";
        ownerEl.textContent = "FREE / UNLOCKED";
        ownerEl.className = "p-3 border border-primary rounded-3 bg-primary-subtle text-primary font-mono fw-bold fs-4";
        statusText.textContent = "Resource is currently free. Any process can acquire lock.";
    }

    if (m.waiting_queue.length === 0) {
        queueContainer.innerHTML = '<span class="text-muted small">Queue empty. No processes waiting.</span>';
    } else {
        queueContainer.innerHTML = m.waiting_queue.map(pid => `
            <span class="badge badge-waiting fs-6">${pid}</span>
        `).join("");
    }

    if (m.history) {
        historyContainer.innerHTML = m.history.map(msg => `
            <div class="log-entry">
                <span class="log-module log-mod-synchronization">MUTEX</span>
                <span class="log-msg-info">${msg}</span>
            </div>
        `).join("");
    }
}

function renderSemaphoreState(s) {
    document.getElementById("sem-max-permits-text").textContent = s.max_permits;
    document.getElementById("sem-current-permits").textContent = s.current_permits;
    document.getElementById("sem-permits-badge").textContent = `Permits Left: ${s.current_permits}`;

    const activeContainer = document.getElementById("sem-active-procs");
    if (s.active_processes.length === 0) {
        activeContainer.innerHTML = '<span class="text-muted small">None</span>';
    } else {
        activeContainer.innerHTML = s.active_processes.map(pid => `
            <span class="badge badge-running fs-6">${pid}</span>
        `).join("");
    }

    const queueContainer = document.getElementById("sem-waiting-queue");
    if (s.waiting_queue.length === 0) {
        queueContainer.innerHTML = '<span class="text-muted small">Queue empty.</span>';
    } else {
        queueContainer.innerHTML = s.waiting_queue.map(pid => `
            <span class="badge badge-waiting fs-6">${pid}</span>
        `).join("");
    }

    const historyContainer = document.getElementById("sem-history-container");
    if (s.history) {
        historyContainer.innerHTML = s.history.map(msg => `
            <div class="log-entry">
                <span class="log-module log-mod-synchronization">SEMAPHORE</span>
                <span class="log-msg-info">${msg}</span>
            </div>
        `).join("");
    }
}

async function mutexAcquire() {
    const input = document.getElementById("mutex-input-pid");
    const pid = input.value.trim();
    if (!pid) return;

    const res = await apiRequest("/api/sync/mutex/acquire", "POST", { pid: pid });
    if (res.success) {
        showToast("Mutex Action", res.message, res.status === "ACQUIRED" ? "success" : "warning");
        // Auto increment pid suggestion
        const nextNum = (parseInt(pid.replace(/\D/g, '')) || 100) + 1;
        input.value = `P${nextNum}`;
        loadSyncState();
    } else {
        showToast("Acquire Failed", res.message, "danger");
    }
}

async function mutexRelease() {
    // Current owner
    const ownerText = document.getElementById("mutex-current-owner").textContent;
    const match = ownerText.match(/^([A-Za-z0-9]+)/);
    const pid = match ? match[1] : null;

    if (!pid || pid === "FREE") {
        showToast("Release Failed", "No process currently holds the lock.", "warning");
        return;
    }

    const res = await apiRequest("/api/sync/mutex/release", "POST", { pid: pid });
    if (res.success) {
        showToast("Mutex Released", res.message, "info");
        loadSyncState();
    } else {
        showToast("Release Failed", res.message, "danger");
    }
}

async function semaphoreWait() {
    const input = document.getElementById("sem-input-pid");
    const pid = input.value.trim();
    if (!pid) return;

    const res = await apiRequest("/api/sync/semaphore/wait", "POST", { pid: pid });
    if (res.success) {
        showToast("Semaphore Wait", res.message, res.status === "GRANTED" ? "success" : "warning");
        const nextNum = (parseInt(pid.replace(/\D/g, '')) || 200) + 1;
        input.value = `P${nextNum}`;
        loadSyncState();
    }
}

async function semaphoreSignal() {
    const res = await apiRequest("/api/sync/semaphore/signal", "POST", {});
    if (res.success) {
        showToast("Semaphore Signal", res.message, "info");
        loadSyncState();
    }
}

async function resetSync() {
    const permits = parseInt(document.getElementById("sem-config-permits").value) || 2;
    const res = await apiRequest("/api/sync/reset", "POST", { max_permits: permits });
    if (res.success) {
        showToast("Synchronization Reset", "Mutex and Semaphore locks reset.", "info");
        loadSyncState();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadSyncState();
});
