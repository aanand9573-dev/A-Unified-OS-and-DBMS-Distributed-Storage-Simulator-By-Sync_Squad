/**
 * Memory Management Controller
 */

let memoryDonutChart = null;

async function loadMemoryData() {
    const res = await apiRequest("/api/memory/metrics");
    if (!res || !res.success) return;

    const m = res.metrics;

    // Update KPI Cards
    document.getElementById("mem-total-val").textContent = `${m.total_memory} MB`;
    document.getElementById("mem-used-val").textContent = `${m.used_memory} MB (${m.utilization_percentage}%)`;
    document.getElementById("mem-free-val").textContent = `${m.free_memory} MB`;
    document.getElementById("mem-frag-val").textContent = `${m.external_fragmentation} MB`;

    // Render Memory Map Bar
    renderMemoryMapBar(m.blocks, m.total_memory);

    // Render Memory Table
    renderMemoryTable(m.blocks);

    // Render Donut Chart
    renderMemoryDonutChart(m.used_memory, m.free_memory);
}

function renderMemoryMapBar(blocks, totalMemory) {
    const container = document.getElementById("visual-memory-map");
    if (!container) return;

    if (!blocks || blocks.length === 0) {
        container.innerHTML = '<div class="text-muted small m-auto">Memory is empty.</div>';
        return;
    }

    container.innerHTML = blocks.map(b => {
        const widthPercent = Math.max(5, (b.size / totalMemory) * 100);
        if (b.is_allocated) {
            return `
                <div class="memory-block-item memory-block-allocated" 
                     style="flex: ${b.size}; min-width: 60px;" 
                     onclick="releaseMemory('${b.pid}')"
                     title="Click to release ${b.pid} (${b.size} MB)">
                    <div class="fw-bold">${b.pid}</div>
                    <div>${b.size} MB</div>
                    <div class="memory-block-address">${b.start_address}-${b.end_address}MB</div>
                </div>
            `;
        } else {
            return `
                <div class="memory-block-item memory-block-free" 
                     style="flex: ${b.size}; min-width: 50px;" 
                     title="FREE Block (${b.size} MB)">
                    <div class="fw-bold text-muted">FREE</div>
                    <div>${b.size} MB</div>
                    <div class="memory-block-address">${b.start_address}-${b.end_address}MB</div>
                </div>
            `;
        }
    }).join("");
}

function renderMemoryTable(blocks) {
    const tbody = document.getElementById("memory-table-body");
    if (!tbody) return;

    tbody.innerHTML = blocks.map(b => `
        <tr>
            <td class="font-mono fw-bold">Block #${b.block_id}</td>
            <td class="font-mono">${b.start_address} MB</td>
            <td class="font-mono">${b.end_address} MB</td>
            <td class="font-mono fw-bold">${b.size} MB</td>
            <td>
                ${b.is_allocated ? 
                    '<span class="badge badge-running">ALLOCATED</span>' : 
                    '<span class="badge badge-new">FREE BLOCK</span>'}
            </td>
            <td>
                ${b.is_allocated ? 
                    `<strong class="text-primary font-mono">${b.pid}</strong> (${b.process_name || 'User App'})` : 
                    '<span class="text-muted">--</span>'}
            </td>
            <td>
                ${b.is_allocated ? 
                    `<button class="btn btn-sm btn-outline-danger" onclick="releaseMemory('${b.pid}')"><i class="fas fa-trash me-1"></i>Release</button>` : 
                    '<span class="text-muted">Available</span>'}
            </td>
        </tr>
    `).join("");
}

function renderMemoryDonutChart(used, free) {
    const ctx = document.getElementById("chart-mem-donut");
    if (!ctx) return;

    if (memoryDonutChart) {
        memoryDonutChart.data.datasets[0].data = [used, free];
        memoryDonutChart.update();
        return;
    }

    memoryDonutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Used RAM (MB)", "Free RAM (MB)"],
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
                    position: "right",
                    labels: { color: "#f8fafc", font: { family: "Outfit" } }
                }
            }
        }
    });
}

async function releaseMemory(target) {
    if (confirm(`Release memory block allocated to ${target}?`)) {
        const res = await apiRequest("/api/memory/release", "POST", { target: target });
        if (res.success) {
            showToast("Memory Released", res.message, "warning");
            loadMemoryData();
        } else {
            showToast("Release Failed", res.message, "danger");
        }
    }
}

async function resetMemory() {
    const res = await apiRequest("/api/memory/reset", "POST", { total_size: 1000 });
    if (res.success) {
        showToast("Memory Reset", "Memory manager reset to initial partition state.", "info");
        loadMemoryData();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadMemoryData();

    const form = document.getElementById("form-memory-allocation");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const pid = document.getElementById("mem-input-pid").value.trim();
            const name = document.getElementById("mem-input-name").value.trim();
            const size = parseInt(document.getElementById("mem-input-size").value);
            const algo = document.getElementById("mem-input-algo").value;

            const res = await apiRequest("/api/memory/allocate", "POST", {
                pid: pid,
                process_name: name,
                size: size,
                algorithm: algo
            });

            if (res.success) {
                showToast("Memory Allocated", res.message, "success");
                form.reset();
                document.getElementById("mem-input-algo").value = algo;
                loadMemoryData();
            } else {
                showToast("Allocation Failed", res.message, "danger");
            }
        });
    }
});
