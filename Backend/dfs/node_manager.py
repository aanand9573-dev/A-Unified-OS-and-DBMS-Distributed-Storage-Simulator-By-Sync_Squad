"""
Node Manager Module
Manages storage node configurations, capacities, online/offline status, and folder operations.
"""

import os
from backend.models.metadata_store import metadata_store
from backend.utils.logger import logger

class NodeManager:
    def get_all_nodes(self):
        nodes_list = []
        for nid, n in metadata_store.nodes.items():
            # Update actual disk usage from stored block files
            used_bytes = 0
            if os.path.exists(n["folder_path"]):
                for fname in os.listdir(n["folder_path"]):
                    fp = os.path.join(n["folder_path"], fname)
                    if os.path.isfile(fp):
                        used_bytes += os.path.getsize(fp)
            
            used_mb = round(used_bytes / (1024 * 1024), 2)
            n["used_mb"] = used_mb
            n["free_mb"] = max(0.0, round(n["capacity_mb"] - used_mb, 2))
            nodes_list.append(dict(n))
        return nodes_list

    def get_online_nodes(self):
        all_nodes = self.get_all_nodes()
        return [n for n in all_nodes if n["status"] == "ONLINE"]

    def set_node_status(self, node_id, status):
        if node_id not in metadata_store.nodes:
            raise KeyError(f"Storage node {node_id} not found.")
        
        status = status.upper()
        if status not in ["ONLINE", "OFFLINE"]:
            raise ValueError("Status must be ONLINE or OFFLINE.")
            
        metadata_store.nodes[node_id]["status"] = status
        lvl = "success" if status == "ONLINE" else "danger"
        logger.log("SYSTEM", lvl, f"Storage Node {node_id} status changed to {status}.")
        return metadata_store.nodes[node_id]

    def add_node(self, name, capacity_mb=500):
        next_idx = len(metadata_store.nodes) + 1
        node_id = f"node{next_idx}"
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        folder_path = os.path.join(base_dir, "storage", node_id)
        os.makedirs(folder_path, exist_ok=True)
        
        node_data = {
            "id": node_id,
            "name": name or f"Storage Node {next_idx}",
            "folder_path": folder_path,
            "capacity_mb": float(capacity_mb),
            "used_mb": 0.0,
            "free_mb": float(capacity_mb),
            "status": "ONLINE"
        }
        metadata_store.nodes[node_id] = node_data
        logger.log("SYSTEM", "success", f"New storage node {node_id} ({name}) created.")
        return node_data

node_manager = NodeManager()
