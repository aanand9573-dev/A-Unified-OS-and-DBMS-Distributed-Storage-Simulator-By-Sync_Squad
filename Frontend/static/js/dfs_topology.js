/**
 * DFS Topology Controller
 */

let topologyData = null;

async function loadTopologyData() {
    const res = await apiRequest("/api/dfs/topology");
    if (!res || !res.success) return;

    topologyData = res;
    renderTopologyGraph(res.nodes, res.topology);
    populateNodeSelect(res.nodes);
    inspectNodeFiles();
}

function renderTopologyGraph(nodes, files) {
    const container = document.getElementById("topology-graph-container");
    if (!container) return;

    if (!files || files.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted my-5">
                <i class="fas fa-folder-open fs-1 text-secondary mb-3 d-block"></i>
                <div>No files currently stored in DFS.</div>
                <small class="text-muted">Go to <a href="/dfs" class="text-primary fw-bold">DFS File Manager</a> to upload files.</small>
            </div>
        `;
        return;
    }

    let graphHtml = "";

    files.forEach(f => {
        graphHtml += `
            <div class="mb-5 p-3 border border-secondary rounded-3 bg-dark">
                <!-- File Tree Root Header -->
                <div class="d-flex align-items-center gap-2 mb-3 pb-2 border-bottom border-secondary">
                    <i class="fas fa-file-pdf text-danger fs-4"></i>
                    <div>
                        <div class="fw-bold text-white fs-5">${f.name}</div>
                        <small class="text-muted font-mono">Size: ${f.size_mb} MB | Total Blocks: ${f.total_blocks} (Block Size: ${f.block_size_mb} MB)</small>
                    </div>
                </div>

                <!-- Node Distribution Columns Grid -->
                <div class="row g-3">
        `;

        nodes.forEach(n => {
            const isOnline = n.status === "ONLINE";
            const primaryBlocks = f.blocks_detail.filter(b => b.primary_node === n.name);
            const replicaBlocks = f.blocks_detail.filter(b => b.replica_node === n.name);

            graphHtml += `
                <div class="col-md-3">
                    <div class="p-3 border ${isOnline ? 'border-primary' : 'border-danger'} rounded-3 bg-dark-subtle text-center">
                        <div class="fw-bold text-white mb-1">
                            <i class="fas fa-server ${isOnline ? 'text-primary' : 'text-danger'} me-1"></i>
                            ${n.name}
                        </div>
                        <span class="badge ${isOnline ? 'badge-running' : 'badge-terminated'} mb-3">${n.status}</span>

                        <!-- Primary Blocks -->
                        <div class="mb-2 text-start">
                            <small class="text-muted uppercase fw-bold d-block mb-1" style="font-size: 0.7rem;">PRIMARY BLOCKS:</small>
                            ${primaryBlocks.length > 0 ? 
                                primaryBlocks.map(b => `<span class="badge bg-primary-subtle text-primary font-mono me-1 mb-1">${b.id}</span>`).join("") : 
                                '<span class="text-muted small">None</span>'}
                        </div>

                        <!-- Replica Blocks -->
                        <div class="text-start">
                            <small class="text-muted uppercase fw-bold d-block mb-1" style="font-size: 0.7rem;">REPLICA BLOCKS:</small>
                            ${replicaBlocks.length > 0 ? 
                                replicaBlocks.map(b => `<span class="badge bg-success-subtle text-success font-mono me-1 mb-1">${b.id}</span>`).join("") : 
                                '<span class="text-muted small">None</span>'}
                        </div>
                    </div>
                </div>
            `;
        });

        graphHtml += `
                </div>
            </div>
        `;
    });

    container.innerHTML = graphHtml;
}

function populateNodeSelect(nodes) {
    const select = document.getElementById("select-node-inspector");
    if (!select) return;

    select.innerHTML = nodes.map(n => `
        <option value="${n.id}">${n.name} (${n.folder_path})</option>
    `).join("");
}

function inspectNodeFiles() {
    const select = document.getElementById("select-node-inspector");
    if (!select || !topologyData) return;

    const nodeId = select.value;
    const node = topologyData.nodes.find(n => n.id === nodeId);
    if (!node) return;

    const tbody = document.getElementById("node-files-tbody");
    let rowsHtml = "";

    topologyData.topology.forEach(f => {
        f.blocks_detail.forEach(b => {
            if (b.primary_node === node.name) {
                rowsHtml += `
                    <tr>
                        <td class="font-mono text-white fw-bold">${b.block_filename || f.name + '_' + b.id + '.block'}</td>
                        <td class="font-mono text-primary">${b.id}</td>
                        <td><span class="badge badge-running">PRIMARY BLOCK</span></td>
                        <td class="font-mono">${b.size_bytes} B</td>
                        <td class="font-mono small text-secondary">${node.folder_path}</td>
                    </tr>
                `;
            }
            if (b.replica_node === node.name) {
                rowsHtml += `
                    <tr>
                        <td class="font-mono text-white fw-bold">${b.block_filename ? 'REPLICA_' + b.block_filename : 'REPLICA_' + b.id + '.block'}</td>
                        <td class="font-mono text-success">${b.id}</td>
                        <td><span class="badge badge-ready">REPLICA BLOCK</span></td>
                        <td class="font-mono">${b.size_bytes} B</td>
                        <td class="font-mono small text-secondary">${node.folder_path}</td>
                    </tr>
                `;
            }
        });
    });

    if (!rowsHtml) {
        rowsHtml = `<tr><td colspan="5" class="text-center text-muted">No block files currently stored on ${node.name}.</td></tr>`;
    }

    tbody.innerHTML = rowsHtml;
}

document.addEventListener("DOMContentLoaded", () => {
    loadTopologyData();
});
