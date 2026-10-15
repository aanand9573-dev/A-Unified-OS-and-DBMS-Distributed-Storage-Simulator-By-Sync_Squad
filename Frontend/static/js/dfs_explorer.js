/**
 * DFS Explorer Controller
 */

let currentFolderId = "root";

async function loadNodes() {
    const res = await apiRequest("/api/dfs/nodes");
    if (!res || !res.success) return;

    const nodes = res.nodes;
    const container = document.getElementById("nodes-container");
    if (!container) return;

    container.innerHTML = nodes.map(n => {
        const isOnline = n.status === "ONLINE";
        const percent = Math.min(100, Math.round((n.used_mb / n.capacity_mb) * 100));

        return `
            <div class="col-xl-3 col-md-6">
                <div class="p-3 border ${isOnline ? 'border-secondary-subtle' : 'border-danger'} rounded-3 bg-dark-subtle position-relative">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <div class="fw-bold text-white fs-6">
                            <i class="fas fa-server ${isOnline ? 'text-primary' : 'text-danger'} me-1"></i>
                            ${n.name}
                        </div>
                        <span class="badge ${isOnline ? 'badge-running' : 'badge-terminated'}">${n.status}</span>
                    </div>

                    <div class="small text-secondary mb-1">
                        Usage: <strong class="text-white">${n.used_mb} MB</strong> / ${n.capacity_mb} MB (${percent}%)
                    </div>
                    <div class="progress mb-3" style="height: 6px; background: rgba(255,255,255,0.05);">
                        <div class="progress-bar ${isOnline ? 'bg-primary' : 'bg-danger'}" style="width: ${percent}%"></div>
                    </div>

                    <div class="d-flex gap-2">
                        <button class="btn btn-xs ${isOnline ? 'btn-outline-danger' : 'btn-outline-success'} flex-grow-1 py-1" style="font-size: 0.75rem;" onclick="toggleNodeStatus('${n.id}', '${isOnline ? 'OFFLINE' : 'ONLINE'}')">
                            <i class="fas ${isOnline ? 'fa-power-off' : 'fa-play'} me-1"></i>
                            ${isOnline ? 'Fail Node' : 'Bring Online'}
                        </button>
                        <button class="btn btn-xs btn-outline-secondary py-1" style="font-size: 0.75rem;" onclick="openConfigNodeModal('${n.id}', '${n.name}', ${n.capacity_mb})" title="Edit Capacity">
                            <i class="fas fa-sliders-h"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

async function loadExplorer(folderId = "root") {
    currentFolderId = folderId;
    const res = await apiRequest(`/api/dfs/explorer?folder_id=${folderId}`);
    if (!res || !res.success) return;

    const cf = res.current_folder;
    const subfolders = res.subfolders;
    const files = res.files;
    const breadcrumbs = res.breadcrumbs || [{ id: "root", name: "Root" }];

    // Render Breadcrumb Trail
    const trailContainer = document.getElementById("breadcrumb-trail");
    if (trailContainer) {
        trailContainer.innerHTML = breadcrumbs.map((b, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            if (isLast) {
                return `<span class="badge bg-primary text-white font-mono px-2 py-1">${b.name}</span>`;
            } else {
                return `<a href="#" onclick="loadExplorer('${b.id}')" class="text-decoration-none text-light font-mono small hover-underline">${b.name}</a> <span class="text-secondary">/</span>`;
            }
        }).join(" ");
    }

    const tbody = document.getElementById("dfs-table-body");
    if (!tbody) return;

    let rowsHtml = "";

    // Show Parent Folder (..) row if not root
    if (cf.parent_id) {
        rowsHtml += `
            <tr class="table-dark-subtle">
                <td style="width: 50px;"><i class="fas fa-level-up-alt text-warning fs-5"></i></td>
                <td class="fw-bold"><a href="#" onclick="loadExplorer('${cf.parent_id}')" class="text-decoration-none text-warning font-mono">.. (Parent Directory)</a></td>
                <td class="text-muted">--</td>
                <td class="text-muted">--</td>
                <td class="text-muted">--</td>
                <td class="small text-muted">--</td>
                <td><button class="btn btn-sm btn-outline-custom" onclick="loadExplorer('${cf.parent_id}')"><i class="fas fa-arrow-up me-1"></i>Up</button></td>
            </tr>
        `;
    }

    // Subfolders
    rowsHtml += subfolders.map(sf => `
        <tr>
            <td style="width: 50px;"><i class="fas fa-folder text-purple fs-5"></i></td>
            <td class="fw-bold"><a href="#" onclick="loadExplorer('${sf.id}')" class="text-decoration-none text-white">${sf.name}</a></td>
            <td class="text-muted font-mono">--</td>
            <td class="text-muted">--</td>
            <td class="text-muted">--</td>
            <td class="small text-muted font-mono">${sf.created_at}</td>
            <td>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-custom" onclick="loadExplorer('${sf.id}')"><i class="fas fa-folder-open me-1"></i>Open</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDfsFolder('${sf.id}')" title="Delete Directory"><i class="fas fa-trash"></i></button>
                </div>
            </td>
        </tr>
    `).join("");

    // Files
    rowsHtml += files.map(f => `
        <tr>
            <td style="width: 50px;"><i class="fas fa-file-alt text-primary fs-5"></i></td>
            <td class="fw-bold text-white">
                <div>${f.name}</div>
                ${f.checksum ? `<small class="text-muted font-mono" style="font-size: 0.7rem;">MD5: ${f.checksum}</small>` : ''}
            </td>
            <td class="font-mono text-light">${f.size_mb} MB <small class="text-secondary">(${f.size_bytes} B)</small></td>
            <td class="font-mono"><span class="badge bg-primary-subtle text-primary">${f.total_blocks} Blocks (${f.block_size_mb}MB/blk)</span></td>
            <td><span class="badge bg-success-subtle text-success">2-Way Replicated</span></td>
            <td class="small text-muted font-mono">${f.created_at}</td>
            <td>
                <div class="d-flex gap-1">
                    <a href="/api/dfs/download/${f.id}" class="btn btn-sm btn-outline-success" title="Download Reconstructed File">
                        <i class="fas fa-download"></i>
                    </a>
                    <button class="btn btn-sm btn-outline-warning" onclick="openRenameModal('${f.id}', '${f.name}')" title="Rename File">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${(f.name.endsWith('.txt') || f.name.endsWith('.log') || f.name.endsWith('.json') || f.name.endsWith('.py')) ? 
                        `<button class="btn btn-sm btn-outline-info" onclick="viewTextFile('${f.id}', '${f.name}')" title="View Text Content"><i class="fas fa-eye"></i></button>` : 
                        `<a href="/api/dfs/preview/${f.id}" target="_blank" class="btn btn-sm btn-outline-info" title="Preview File"><i class="fas fa-external-link-alt"></i></a>`}
                    <button class="btn btn-sm btn-outline-primary" onclick="viewFileDetails('${f.id}')" title="Block Layout Metadata">
                        <i class="fas fa-cubes"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteDfsFile('${f.id}')" title="Delete File">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join("");

    if (!rowsHtml) {
        rowsHtml = '<tr><td colspan="7" class="text-center text-muted py-4">Directory is empty. Click "Upload Real File" or "Create Text File" to store files.</td></tr>';
    }

    tbody.innerHTML = rowsHtml;
}

async function toggleNodeStatus(nodeId, newStatus) {
    const res = await apiRequest("/api/dfs/nodes/status", "POST", { node_id: nodeId, status: newStatus });
    if (res && res.success) {
        if (newStatus === "OFFLINE") {
            const rec = res.recovery_info;
            showToast("Node Failure Simulated", `Node ${nodeId} set to OFFLINE. Recoverable blocks via replicas: ${rec ? rec.recoverable_count : 0}`, "warning");
        } else {
            showToast("Node Restored", `Node ${nodeId} is back ONLINE.`, "success");
        }
        loadNodes();
        loadExplorer(currentFolderId);
    }
}

async function loadAllocationAlgorithm() {
    const res = await apiRequest("/api/dfs/allocation_algorithm");
    if (res && res.success) {
        const selectEl = document.getElementById("select-active-allocation-algo");
        if (selectEl) {
            selectEl.value = res.active_algorithm;
        }
    }
}

async function updateClusterAllocationAlgorithm(val) {
    const res = await apiRequest("/api/dfs/allocation_algorithm", "POST", { algorithm: val });
    if (res && res.success) {
        showToast("Allocation Algorithm Updated", `Cluster node allocation set to ${res.active_algorithm}.`, "info");
    } else {
        showToast("Update Failed", res ? res.message : "Error", "danger");
    }
}

async function repairClusterReplication() {
    const selectEl = document.getElementById("select-active-allocation-algo");
    const algo = selectEl ? selectEl.value : "ROUND_ROBIN";
    showToast("Cluster Repair", `Scanning storage nodes for under-replicated block copies using [${algo}]...`, "info");
    const res = await apiRequest("/api/dfs/recover", "POST", { algorithm: algo });
    if (res && res.success) {
        showToast("Repair Finished", res.message, "success");
        loadNodes();
        loadExplorer(currentFolderId);
    } else {
        showToast("Repair Failed", res ? res.message : "Error running cluster repair.", "danger");
    }
}

function openConfigNodeModal(nodeId, nodeName, currentCap) {
    document.getElementById("config-node-id").value = nodeId;
    document.getElementById("config-node-name-disp").value = `${nodeName} (${nodeId})`;
    document.getElementById("config-node-cap-input").value = currentCap;
    const modal = new bootstrap.Modal(document.getElementById("configNodeModal"));
    modal.show();
}

function openRenameModal(fileId, currentName) {
    document.getElementById("rename-file-id").value = fileId;
    document.getElementById("rename-new-filename").value = currentName;
    const modal = new bootstrap.Modal(document.getElementById("renameFileModal"));
    modal.show();
}

async function viewFileDetails(fileId) {
    const res = await apiRequest(`/api/dfs/file/${fileId}`);
    if (!res || !res.success) return;

    const f = res.file;
    document.getElementById("details-file-title").innerHTML = `<i class="fas fa-info-circle text-info me-2"></i>Block Layout Metadata: ${f.name}`;

    document.getElementById("details-file-summary").innerHTML = `
        <div class="col-md-3"><small class="text-muted d-block">FILE ID</small><span class="font-mono text-primary fw-bold">${f.id}</span></div>
        <div class="col-md-3"><small class="text-muted d-block">FILE SIZE</small><span class="font-mono text-white">${f.size_mb} MB (${f.size_bytes} B)</span></div>
        <div class="col-md-3"><small class="text-muted d-block">BLOCK SIZE</small><span class="font-mono text-warning">${f.block_size_mb} MB / Block</span></div>
        <div class="col-md-3"><small class="text-muted d-block">TOTAL BLOCKS</small><span class="font-mono text-success">${f.total_blocks} Blocks</span></div>
        ${f.checksum ? `<div class="col-12 mt-1"><small class="text-muted d-block">MD5 CHECKSUM</small><span class="font-mono text-cyan">${f.checksum}</span></div>` : ''}
    `;

    const tbody = document.getElementById("details-blocks-tbody");
    tbody.innerHTML = f.blocks_detail.map(b => `
        <tr>
            <td class="font-mono fw-bold text-primary">${b.id}</td>
            <td class="font-mono">${b.size_bytes} B</td>
            <td class="font-mono small text-muted">${b.checksum}</td>
            <td>
                <span class="badge ${b.primary_node_status === 'ONLINE' ? 'badge-running' : 'badge-terminated'} me-1">${b.primary_node}</span>
                <span class="small text-muted">(PRIMARY)</span>
            </td>
            <td>
                <span class="badge ${b.replica_node_status === 'ONLINE' ? 'badge-ready' : 'badge-terminated'} me-1">${b.replica_node}</span>
                <span class="small text-muted">(REPLICA)</span>
            </td>
        </tr>
    `).join("");

    const modal = new bootstrap.Modal(document.getElementById("fileDetailsModal"));
    modal.show();
}

async function viewTextFile(fileId, filename) {
    const res = await apiRequest(`/api/dfs/view_text/${fileId}`);
    if (!res || !res.success) return;

    document.getElementById("view-text-title").textContent = `Viewing Document: ${filename}`;
    document.getElementById("view-text-body").textContent = res.content;
    const modal = new bootstrap.Modal(document.getElementById("viewTextModal"));
    modal.show();
}

async function deleteDfsFile(fileId) {
    if (confirm("Delete file and remove block files from all storage nodes?")) {
        const res = await apiRequest(`/api/dfs/file/${fileId}`, "DELETE");
        if (res && res.success) {
            showToast("File Deleted", "File metadata and block files removed.", "warning");
            loadExplorer(currentFolderId);
            loadNodes();
        }
    }
}

async function deleteDfsFolder(folderId) {
    if (confirm("Delete directory and all its files?")) {
        const res = await apiRequest(`/api/dfs/folder/${folderId}`, "DELETE");
        if (res && res.success) {
            showToast("Directory Deleted", res.message, "warning");
            loadExplorer(currentFolderId);
            loadNodes();
        } else {
            showToast("Delete Failed", res ? res.message : "Error deleting folder", "danger");
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadNodes();
    loadExplorer();
    loadAllocationAlgorithm();

    // Upload Form Submit
    const uploadForm = document.getElementById("form-upload-file");
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById("upload-file-input");
            const blockSize = document.getElementById("upload-block-size").value;
            const algoSelect = document.getElementById("upload-allocation-algo");

            if (fileInput.files.length === 0) return;

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("block_size_mb", blockSize);
            formData.append("folder_id", currentFolderId);
            if (algoSelect && algoSelect.value !== "DEFAULT") {
                formData.append("allocation_algorithm", algoSelect.value);
            }

            showToast("Uploading File", "Splitting file into blocks & distributing to nodes...", "info");

            try {
                const response = await fetch("/api/dfs/upload", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                if (data.success) {
                    showToast("Upload Successful", data.message, "success");
                    const modal = bootstrap.Modal.getInstance(document.getElementById("uploadFileModal"));
                    if (modal) modal.hide();
                    uploadForm.reset();
                    loadExplorer(currentFolderId);
                    loadNodes();
                } else {
                    showToast("Upload Failed", data.message, "danger");
                }
            } catch (err) {
                showToast("Upload Error", err.message, "danger");
            }
        });
    }

    // Text File Form Submit
    const textForm = document.getElementById("form-create-text-file");
    if (textForm) {
        textForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const filename = document.getElementById("text-filename").value.trim();
            const content = document.getElementById("text-content").value;
            const algoSelect = document.getElementById("text-allocation-algo");
            const algo = (algoSelect && algoSelect.value !== "DEFAULT") ? algoSelect.value : undefined;

            const res = await apiRequest("/api/dfs/create_file", "POST", {
                filename: filename,
                content: content,
                folder_id: currentFolderId,
                allocation_algorithm: algo
            });

            if (res && res.success) {
                showToast("Text File Created", res.message, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("createTextFileModal"));
                if (modal) modal.hide();
                textForm.reset();
                loadExplorer(currentFolderId);
                loadNodes();
            } else {
                showToast("Creation Failed", res ? res.message : "Error", "danger");
            }
        });
    }

    // Folder Form Submit
    const folderForm = document.getElementById("form-create-folder");
    if (folderForm) {
        folderForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const folderName = document.getElementById("folder-name-input").value.trim();

            const res = await apiRequest("/api/dfs/create_folder", "POST", {
                folder_name: folderName,
                parent_id: currentFolderId
            });

            if (res && res.success) {
                showToast("Directory Created", `Created folder ${folderName}.`, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("createFolderModal"));
                if (modal) modal.hide();
                folderForm.reset();
                loadExplorer(currentFolderId);
            }
        });
    }

    // Add Node Form Submit
    const nodeForm = document.getElementById("form-add-node");
    if (nodeForm) {
        nodeForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("node-name-input").value.trim();
            const cap = parseFloat(document.getElementById("node-cap-input").value);

            const res = await apiRequest("/api/dfs/nodes", "POST", { name: name, capacity_mb: cap });
            if (res && res.success) {
                showToast("Node Initialized", `Created storage node ${res.node.id}.`, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("addNodeModal"));
                if (modal) modal.hide();
                nodeForm.reset();
                loadNodes();
            }
        });
    }

    // Rename Form Submit
    const renameForm = document.getElementById("form-rename-file");
    if (renameForm) {
        renameForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileId = document.getElementById("rename-file-id").value;
            const newName = document.getElementById("rename-new-filename").value.trim();

            const res = await apiRequest("/api/dfs/rename", "POST", { file_id: fileId, new_name: newName });
            if (res && res.success) {
                showToast("File Renamed", res.message, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("renameFileModal"));
                if (modal) modal.hide();
                loadExplorer(currentFolderId);
            } else {
                showToast("Rename Failed", res ? res.message : "Error", "danger");
            }
        });
    }

    // Config Node Capacity Form Submit
    const configNodeForm = document.getElementById("form-config-node");
    if (configNodeForm) {
        configNodeForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const nodeId = document.getElementById("config-node-id").value;
            const cap = parseFloat(document.getElementById("config-node-cap-input").value);

            const res = await apiRequest("/api/dfs/nodes/capacity", "POST", { node_id: nodeId, capacity_mb: cap });
            if (res && res.success) {
                showToast("Capacity Updated", res.message, "success");
                const modal = bootstrap.Modal.getInstance(document.getElementById("configNodeModal"));
                if (modal) modal.hide();
                loadNodes();
            } else {
                showToast("Update Failed", res ? res.message : "Error", "danger");
            }
        });
    }
});
