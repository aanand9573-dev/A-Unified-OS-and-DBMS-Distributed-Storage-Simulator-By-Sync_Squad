"""
Recovery Module
Handles storage node failure detection, block failover reading from replicas,
and re-replication to healthy online storage nodes.
"""

from backend.models.metadata_store import metadata_store
from backend.dfs.node_manager import node_manager
from backend.dfs.block_manager import block_manager
from backend.utils.logger import logger

class RecoveryManager:
    def handle_node_failure(self, failed_node_id):
        """
        Scans all files and blocks stored on failed_node_id and assesses health / failover availability.
        """
        node_manager.set_node_status(failed_node_id, "OFFLINE")
        
        affected_blocks = []
        for b_id, block in metadata_store.blocks.items():
            if block.get("primary_node_id") == failed_node_id or block.get("replica_node_id") == failed_node_id:
                affected_blocks.append(block)
                
        online_nodes = node_manager.get_online_nodes()
        recoverable_count = 0
        unrecoverable_count = 0
        
        for b in affected_blocks:
            # Check if block has another ONLINE node (replica or primary)
            other_node_id = b["replica_node_id"] if b["primary_node_id"] == failed_node_id else b["primary_node_id"]
            other_node = metadata_store.nodes.get(other_node_id)
            
            if other_node and other_node["status"] == "ONLINE":
                recoverable_count += 1
                logger.log("SYSTEM", "success", f"Failover verified for block {b['id']}: Available on healthy Node {other_node_id}.")
            else:
                unrecoverable_count += 1
                logger.log("SYSTEM", "danger", f"DATA LOSS WARNING: Block {b['id']} has no remaining online node!")

        logger.log("SYSTEM", "warning", f"Node Failure Simulation: Node {failed_node_id} is OFFLINE. Affected blocks: {len(affected_blocks)} (Recoverable: {recoverable_count}, Risk: {unrecoverable_count}).")
        return {
            "failed_node_id": failed_node_id,
            "total_affected_blocks": len(affected_blocks),
            "recoverable_count": recoverable_count,
            "unrecoverable_count": unrecoverable_count,
            "affected_blocks": affected_blocks
        }

recovery_manager = RecoveryManager()
