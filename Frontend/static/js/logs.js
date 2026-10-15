/**
 * System Logs Controller
 */

let allLogsData = [];

async function loadLogs() {
    const mod = document.getElementById("select-log-module").value;
    const res = await apiRequest(`/api/logs?module=${mod}&limit=100`);
    if (!res || !res.success) return;

    allLogsData = res.logs;
    renderLogFeed(allLogsData);
}

function renderLogFeed(logs) {
    const container = document.getElementById("full-terminal-logs");
    const countBadge = document.getElementById("log-count-badge");
    if (!container) return;

    countBadge.textContent = `Total Logs: ${logs.length}`;

    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="text-muted small p-2">No activity logs matching criteria.</div>';
        return;
    }

    container.innerHTML = logs.map(l => `
        <div class="log-entry" data-message="${l.message.toLowerCase()}">
            <span class="log-timestamp">[${l.timestamp}]</span>
            <span class="log-module log-mod-${l.module.toLowerCase()}">${l.module}</span>
            <span class="log-msg-${l.level.toLowerCase()}">${l.message}</span>
        </div>
    `).join("");
}

function filterLogRows() {
    const query = document.getElementById("input-log-search").value.toLowerCase().trim();
    if (!query) {
        renderLogFeed(allLogsData);
        return;
    }
    const filtered = allLogsData.filter(l => 
        l.message.toLowerCase().includes(query) || 
        l.module.toLowerCase().includes(query)
    );
    renderLogFeed(filtered);
}

async function clearLogs() {
    if (confirm("Are you sure you want to clear system logs?")) {
        const res = await apiRequest("/api/logs", "DELETE");
        if (res.success) {
            showToast("Logs Cleared", "System activity log feed emptied.", "info");
            loadLogs();
        }
    }
}

function downloadLogs() {
    if (!allLogsData || allLogsData.length === 0) {
        showToast("Download", "No logs to export.", "warning");
        return;
    }

    const lines = allLogsData.map(l => `[${l.timestamp}] [${l.module}] [${l.level.toUpperCase()}]: ${l.message}`);
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `OS_Simulator_Logs_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

document.addEventListener("DOMContentLoaded", () => {
    loadLogs();

    setInterval(() => {
        const auto = document.getElementById("check-auto-refresh");
        if (auto && auto.checked) {
            loadLogs();
        }
    }, 3000);
});
