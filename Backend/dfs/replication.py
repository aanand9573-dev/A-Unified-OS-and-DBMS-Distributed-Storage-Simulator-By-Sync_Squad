"""
Replication Module
Implements block-level 2-way replication across online storage nodes.
"""

from backend.models.metadata_store import metadata_store
from backend.dfs.block_manager import block_manager
from backend.utils.logger import logger

class ReplicationManager:
    def replicate_blocks(self, blocks, online_nodes, replication_factor=2):
        """
        Replicates each block to a distinct secondary online node.
        """
        if len(online_nodes) < 2 or replication_factor < 2:
            logger.log("SYSTEM", "warning", "Replication skipped: Requires at least 2 online storage nodes.")
            return

        for idx, block in enumerate(blocks):
            p_node_id = block["primary_node_id"]
            
            # Candidates for replica: online nodes excluding primary node
            candidates = [n for n in online_nodes if n["id"] != p_node_id]
            if not candidates:
                continue
                
            # Round Robin replica node selection
            r_node = candidates[idx % len(candidates)]
            r_node_id = r_node["id"]
            
            block_manager.save_block_to_node(block, r_node_id, is_replica=True)
            logger.log("SYSTEM", "success", f"Replicated block {block['id']} -> Replica Node {r_node_id} (Primary: {p_node_id}).")

replication_manager = ReplicationManager()
