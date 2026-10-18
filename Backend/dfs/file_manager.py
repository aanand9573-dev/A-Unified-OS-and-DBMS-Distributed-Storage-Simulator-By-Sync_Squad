"""
File Manager Module
Core orchestrator for DFS file operations (Upload, Create, Download/Reconstruction, Delete, View)
and integration with OS simulation processes (Process PCB, Memory Allocation, Disk I/O Queue, Synchronization Mutex).
"""

import os
import uuid
import datetime
import io
from backend.models.metadata_store import metadata_store
from backend.models.simulator_state import simulator_state
from backend.dfs.node_manager import node_manager
from backend.dfs.block_manager import block_manager
from backend.dfs.replication import replication_manager
from backend.utils.logger import logger

class FileManager:
    def upload_file(self, file_name, file_bytes, block_size_mb=2, folder_id="root"):
        """
        Receives real file binary bytes, splits into blocks, places on storage nodes,
        replicates blocks, and triggers OS process & memory management events.
        """
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        size_bytes = len(file_bytes)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # 1. TRIGGER OS PROCESS MANAGEMENT
        pid = f"P{len(simulator_state.process_manager.processes) + 101}"
        proc = simulator_state.process_manager.create_process(
            pid=pid,
            name=f"Upload {file_name}",
            process_type="Storage Task",
            arrival_time=0,
            burst_time=max(2, int(size_mb) + 2),
            priority=1,
            state="RUNNING"
        )

        # 2. TRIGGER SYNCHRONIZATION MUTEX LOCK
        simulator_state.mutex_sim.acquire(pid)

        # 3. TRIGGER SIMULATED MEMORY ALLOCATION
        alloc_size = max(50, int(size_mb * 1.2) + 50)
        mem_res = simulator_state.memory_manager.allocate(pid, alloc_size, "First Fit", f"Upload_{file_name}")

        # 4. SPLIT FILE INTO BLOCKS
        blocks = block_manager.split_bytes_into_blocks(file_id, file_name, file_bytes, block_size_mb)

        # 5. DISTRIBUTE PRIMARY BLOCKS TO ONLINE NODES
        online_nodes = node_manager.get_online_nodes()
        if not online_nodes:
            simulator_state.mutex_sim.release(pid)
            simulator_state.memory_manager.deallocate(pid)
            simulator_state.process_manager.update_state(pid, "TERMINATED")
            raise IOError("No ONLINE storage nodes available to store blocks!")

        for idx, block in enumerate(blocks):
            # Round Robin placement among online nodes
            assigned_node = online_nodes[idx % len(online_nodes)]
            block_manager.save_block_to_node(block, assigned_node["id"], is_replica=False)
            
            # Save to metadata
            metadata_store.blocks[block["id"]] = block

        # 6. REPLICATE BLOCKS (2-way replication)
        replication_manager.replicate_blocks(blocks, online_nodes, replication_factor=2)

        # 7. TRIGGER SIMULATED DISK SCHEDULING REQUESTS
        for b in blocks:
            # Generate track numbers from block index
            track = (b["block_index"] * 37 + 15) % 200
            simulator_state.disk_state["requests"].append(track)

        # 8. SAVE FILE METADATA
        file_meta = {
            "id": file_id,
            "name": file_name,
            "folder_id": folder_id if folder_id in metadata_store.folders else "root",
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "block_size_mb": block_size_mb,
            "total_blocks": len(blocks),
            "block_ids": [b["id"] for b in blocks],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        metadata_store.files[file_id] = file_meta

        # 9. OS CLEANUP & PROCESS TERMINATION
        simulator_state.mutex_sim.release(pid)
        simulator_state.memory_manager.deallocate(pid)
        simulator_state.process_manager.update_state(pid, "TERMINATED")

        logger.log("PROCESS", "success", f"DFS Upload complete: Process {pid} uploaded '{file_name}' ({size_mb} MB) split into {len(blocks)} blocks.")
        return file_meta

    def download_and_reconstruct_file(self, file_id):
        """
        Reconstructs the original file from distributed binary blocks.
        Supports failover reading from replicas if primary nodes are OFFLINE.
        """
        if file_id not in metadata_store.files:
            raise KeyError(f"File {file_id} not found.")

        file_meta = metadata_store.files[file_id]
        file_name = file_meta["name"]

        # 1. TRIGGER OS PROCESS MANAGEMENT
        pid = f"P{len(simulator_state.process_manager.processes) + 101}"
        simulator_state.process_manager.create_process(
            pid=pid,
            name=f"Download {file_name}",
            process_type="Read Task",
            arrival_time=0,
            burst_time=3,
            priority=1,
            state="RUNNING"
        )

        # 2. TRIGGER MEMORY ALLOCATION
        alloc_size = max(40, int(file_meta["size_mb"]) + 30)
        simulator_state.memory_manager.allocate(pid, alloc_size, "Best Fit", f"Download_{file_name}")

        # 3. RETRIEVE BLOCKS IN ORDER & CONCATENATE
        reconstructed_bytes = bytearray()
        block_ids = file_meta["block_ids"]
        retrieved_sources = []

        for b_id in block_ids:
            if b_id not in metadata_store.blocks:
                raise IOError(f"Missing metadata for block {b_id}!")
                
            block_meta = metadata_store.blocks[b_id]
            chunk_bytes, node_id, source_type = block_manager.read_block_data(block_meta)
            reconstructed_bytes.extend(chunk_bytes)
            retrieved_sources.append(f"{b_id} from {node_id} ({source_type})")

            # Add disk track read request
            track = (block_meta["block_index"] * 41 + 10) % 200
            simulator_state.disk_state["requests"].append(track)

        # 4. OS CLEANUP
        simulator_state.memory_manager.deallocate(pid)
        simulator_state.process_manager.update_state(pid, "TERMINATED")

        logger.log("PROCESS", "success", f"DFS Download complete: Process {pid} reconstructed '{file_name}' ({len(reconstructed_bytes)} bytes) from blocks.")
        return bytes(reconstructed_bytes), file_name

    def create_text_file(self, file_name, text_content, folder_id="root"):
        if not file_name.endswith(".txt"):
            file_name += ".txt"
        content_bytes = text_content.encode("utf-8")
        return self.upload_file(file_name, content_bytes, block_size_mb=1, folder_id=folder_id)

    def read_text_file_content(self, file_id):
        file_bytes, filename = self.download_and_reconstruct_file(file_id)
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return f"[Binary File Content: {len(file_bytes)} bytes]"

    def create_folder(self, folder_name, parent_id="root"):
        fid = f"folder_{uuid.uuid4().hex[:6]}"
        parent = metadata_store.folders.get(parent_id, metadata_store.folders["root"])
        path = f"{parent['path'].rstrip('/')}/{folder_name}"
        
        folder_meta = {
            "id": fid,
            "name": folder_name,
            "parent_id": parent["id"],
            "path": path,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        metadata_store.folders[fid] = folder_meta
        logger.log("SYSTEM", "info", f"Created folder '{folder_name}' at path '{path}'.")
        return folder_meta

    def delete_file(self, file_id):
        if file_id not in metadata_store.files:
            return False

        file_meta = metadata_store.files.pop(file_id)
        pid = f"P{len(simulator_state.process_manager.processes) + 101}"
        simulator_state.process_manager.create_process(
            pid=pid,
            name=f"Delete {file_meta['name']}",
            process_type="Clean Task",
            arrival_time=0,
            burst_time=1,
            priority=2,
            state="RUNNING"
        )
        simulator_state.mutex_sim.acquire(pid)

        # Delete physical block files
        for b_id in file_meta["block_ids"]:
            if b_id in metadata_store.blocks:
                b_meta = metadata_store.blocks.pop(b_id)
                block_manager.delete_block_files(b_meta)

        simulator_state.mutex_sim.release(pid)
        simulator_state.process_manager.update_state(pid, "TERMINATED")

        logger.log("PROCESS", "warning", f"Deleted file '{file_meta['name']}' and cleaned up block files.")
        return True

    def get_file_details(self, file_id):
        if file_id not in metadata_store.files:
            return None
        f = dict(metadata_store.files[file_id])
        file_blocks = []
        for b_id in f["block_ids"]:
            if b_id in metadata_store.blocks:
                b = metadata_store.blocks[b_id]
                p_node = metadata_store.nodes.get(b.get("primary_node_id"))
                r_node = metadata_store.nodes.get(b.get("replica_node_id"))
                file_blocks.append({
                    "id": b["id"],
                    "index": b["block_index"],
                    "size_bytes": b["size_bytes"],
                    "size_mb": b["size_mb"],
                    "checksum": b["checksum"],
                    "primary_node": p_node["name"] if p_node else "None",
                    "primary_node_status": p_node["status"] if p_node else "UNKNOWN",
                    "replica_node": r_node["name"] if r_node else "None",
                    "replica_node_status": r_node["status"] if r_node else "UNKNOWN"
                })
        f["blocks_detail"] = file_blocks
        return f

    def list_folder_contents(self, folder_id="root"):
        if folder_id not in metadata_store.folders:
            folder_id = "root"
            
        current_folder = metadata_store.folders[folder_id]
        subfolders = [dict(f) for f in metadata_store.folders.values() if f.get("parent_id") == folder_id]
        files = [dict(f) for f in metadata_store.files.values() if f.get("folder_id") == folder_id]
        
        return {
            "current_folder": current_folder,
            "subfolders": subfolders,
            "files": files
        }

file_manager = FileManager()
