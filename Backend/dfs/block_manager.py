"""
Block Manager Module
Handles file block splitting, physical binary block storage on node folders,
checksum integrity verification, and block retrieval.
"""

import os
import hashlib
from backend.models.metadata_store import metadata_store
from backend.utils.logger import logger

class BlockManager:
    def split_bytes_into_blocks(self, file_id, file_name, file_bytes, block_size_mb=2):
        """
        Splits file_bytes into fixed size binary blocks.
        block_size_mb: size of each block in MB (e.g. 2 MB).
        """
        block_size_bytes = int(block_size_mb * 1024 * 1024)
        total_len = len(file_bytes)
        
        blocks = []
        offset = 0
        block_idx = 1
        
        sanitized_filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in file_name)
        
        while offset < total_len or total_len == 0:
            chunk = file_bytes[offset : offset + block_size_bytes]
            block_id = f"{file_id}_B{block_idx}"
            block_filename = f"{sanitized_filename}_B{block_idx}.block"
            checksum = hashlib.md5(chunk).hexdigest()
            
            block_meta = {
                "id": block_id,
                "file_id": file_id,
                "block_index": block_idx,
                "block_filename": block_filename,
                "size_bytes": len(chunk),
                "size_mb": round(len(chunk) / (1024 * 1024), 3),
                "checksum": checksum,
                "data_chunk": chunk, # Transient chunk bytes
                "primary_node_id": None,
                "replica_node_id": None
            }
            blocks.append(block_meta)
            
            offset += block_size_bytes
            block_idx += 1
            if total_len == 0:
                break
                
        logger.log("SYSTEM", "info", f"File '{file_name}' ({round(total_len / (1024*1024), 2)} MB) split into {len(blocks)} blocks (Block Size: {block_size_mb} MB).")
        return blocks

    def save_block_to_node(self, block_meta, node_id, is_replica=False):
        """
        Physically writes the block bytes into the node folder.
        """
        if node_id not in metadata_store.nodes:
            raise KeyError(f"Storage node {node_id} not found.")
            
        node = metadata_store.nodes[node_id]
        folder_path = node["folder_path"]
        os.makedirs(folder_path, exist_ok=True)
        
        block_filename = block_meta["block_filename"]
        if is_replica:
            block_filename = f"REPLICA_{block_filename}"
            
        file_path = os.path.join(folder_path, block_filename)
        
        with open(file_path, "wb") as f:
            f.write(block_meta["data_chunk"])
            
        if is_replica:
            block_meta["replica_node_id"] = node_id
            block_meta["replica_file_path"] = file_path
        else:
            block_meta["primary_node_id"] = node_id
            block_meta["primary_file_path"] = file_path
            
        tag = "REPLICA" if is_replica else "PRIMARY"
        logger.log("SYSTEM", "success", f"Saved {tag} block {block_meta['id']} ({block_meta['size_bytes']} bytes) -> Node {node_id}.")
        return file_path

    def read_block_data(self, block_meta):
        """
        Reads binary bytes of a block.
        Tries Primary Node first. If Primary Node is OFFLINE, failover to Replica Node!
        """
        p_node_id = block_meta.get("primary_node_id")
        r_node_id = block_meta.get("replica_node_id")
        
        p_node = metadata_store.nodes.get(p_node_id) if p_node_id else None
        r_node = metadata_store.nodes.get(r_node_id) if r_node_id else None
        
        # 1. Try Primary Node if ONLINE
        if p_node and p_node["status"] == "ONLINE":
            fp = block_meta.get("primary_file_path")
            if fp and os.path.exists(fp):
                with open(fp, "rb") as f:
                    return f.read(), p_node_id, "PRIMARY"

        # 2. Failover: Try Replica Node if Primary Node is OFFLINE / missing
        if r_node and r_node["status"] == "ONLINE":
            fp = block_meta.get("replica_file_path")
            if fp and os.path.exists(fp):
                logger.log("SYSTEM", "warning", f"FAILOVER RECOVERY: Primary Node {p_node_id} is OFFLINE. Recovered block {block_meta['id']} from Replica Node {r_node_id}!")
                with open(fp, "rb") as f:
                    return f.read(), r_node_id, "REPLICA_FAILOVER"

        raise IOError(f"Block {block_meta['id']} unavailable! Primary Node ({p_node_id}) and Replica Node ({r_node_id}) are both offline or missing.")

    def delete_block_files(self, block_meta):
        for path_key in ["primary_file_path", "replica_file_path"]:
            fp = block_meta.get(path_key)
            if fp and os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception as e:
                    logger.log("SYSTEM", "warning", f"Error removing block file {fp}: {e}")

block_manager = BlockManager()
