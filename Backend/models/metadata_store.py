"""
Metadata Store Module
Centralized metadata manager for files, blocks, storage nodes, folders, and replication.
Designed to be compatible with MySQL database schema migration in Phase 2.
"""

import os
import time
import json
import datetime
import threading
import hashlib
from backend.utils.logger import logger

class MetadataStore:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetadataStore, cls).__new__(cls)
                cls._instance._init_store()
            return cls._instance

    def _init_store(self):
        self.nodes = {}
        self.files = {}
        self.blocks = {}
        self.folders = {}
        self.active_folder_id = "root"

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.storage_base = os.path.join(base_dir, "storage")
        os.makedirs(self.storage_base, exist_ok=True)
        self.metadata_file = os.path.join(self.storage_base, "metadata.json")

        # Define default root folder
        self.folders["root"] = {
            "id": "root",
            "name": "Root",
            "parent_id": None,
            "path": "/",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Initialize default 4 storage nodes
        default_nodes = [
            ("node1", "Storage Node 1", 500),
            ("node2", "Storage Node 2", 500),
            ("node3", "Storage Node 3", 500),
            ("node4", "Storage Node 4", 500),
        ]

        for nid, name, cap in default_nodes:
            folder_path = os.path.join(self.storage_base, nid)
            os.makedirs(folder_path, exist_ok=True)
            self.nodes[nid] = {
                "id": nid,
                "name": name,
                "folder_path": folder_path,
                "capacity_mb": float(cap),
                "used_mb": 0.0,
                "free_mb": float(cap),
                "status": "ONLINE"
            }

        # Load persisted metadata if file exists
        self.load()

    def save(self):
        """Thread-safe atomic save of metadata to JSON."""
        with self._lock:
            data = {
                "nodes": self.nodes,
                "files": self.files,
                "blocks": self.blocks,
                "folders": self.folders,
                "last_saved": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            tmp_file = self.metadata_file + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                if os.path.exists(self.metadata_file):
                    os.replace(tmp_file, self.metadata_file)
                else:
                    os.rename(tmp_file, self.metadata_file)
            except Exception as e:
                logger.log("SYSTEM", "danger", f"Failed saving metadata: {e}")

    def load(self):
        """Loads and reconciles metadata from JSON if exists."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if "folders" in data and "root" in data["folders"]:
                    self.folders = data["folders"]
                if "files" in data:
                    self.files = data["files"]
                if "blocks" in data:
                    self.blocks = data["blocks"]
                if "nodes" in data:
                    for nid, nmeta in data["nodes"].items():
                        if nid in self.nodes:
                            self.nodes[nid].update(nmeta)
                        else:
                            self.nodes[nid] = nmeta
                            os.makedirs(nmeta["folder_path"], exist_ok=True)

                self.reconcile_storage()
                logger.log("SYSTEM", "info", f"Loaded persistent metadata: {len(self.files)} files, {len(self.blocks)} blocks.")
            except Exception as e:
                logger.log("SYSTEM", "warning", f"Could not load metadata file: {e}")

    def reconcile_storage(self):
        """Re-checks physical block files and updates node used/free metrics."""
        for nid, n in self.nodes.items():
            used_bytes = 0
            if os.path.exists(n["folder_path"]):
                for fname in os.listdir(n["folder_path"]):
                    fp = os.path.join(n["folder_path"], fname)
                    if os.path.isfile(fp):
                        used_bytes += os.path.getsize(fp)
            used_mb = round(used_bytes / (1024 * 1024), 2)
            n["used_mb"] = used_mb
            n["free_mb"] = max(0.0, round(n["capacity_mb"] - used_mb, 2))

    def reset(self):
        with self._lock:
            # Clear physical block files
            for n in self.nodes.values():
                folder_path = n["folder_path"]
                if os.path.exists(folder_path):
                    for filename in os.listdir(folder_path):
                        file_p = os.path.join(folder_path, filename)
                        if os.path.isfile(file_p):
                            try:
                                os.remove(file_p)
                            except Exception:
                                pass
            self.files = {}
            self.blocks = {}
            self.folders = {
                "root": {
                    "id": "root",
                    "name": "Root",
                    "parent_id": None,
                    "path": "/",
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            for n in self.nodes.values():
                n["capacity_mb"] = 500.0
                n["used_mb"] = 0.0
                n["free_mb"] = 500.0
                n["status"] = "ONLINE"
            
            # Remove metadata file or overwrite
            if os.path.exists(self.metadata_file):
                try:
                    os.remove(self.metadata_file)
                except Exception:
                    pass
            self.save()
            logger.log("SYSTEM", "info", "DFS Metadata Store & Node Storage cleared.")

metadata_store = MetadataStore()
