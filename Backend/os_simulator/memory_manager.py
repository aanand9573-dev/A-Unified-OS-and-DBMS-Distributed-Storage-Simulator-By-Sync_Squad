"""
Memory Manager Module
Simulates RAM contiguous dynamic memory allocation using:
1. First Fit
2. Best Fit
3. Worst Fit

Tracks total, used, free memory, external fragmentation, and memory block maps.
Supports adjacent free block coalescing upon release.
"""

from backend.utils.logger import logger

class MemoryBlock:
    def __init__(self, block_id, start_address, size, is_allocated=False, pid=None, process_name=None):
        self.block_id = block_id
        self.start_address = start_address
        self.size = size
        self.end_address = start_address + size
        self.is_allocated = is_allocated
        self.pid = pid
        self.process_name = process_name

    def to_dict(self):
        return {
            "block_id": self.block_id,
            "start_address": self.start_address,
            "end_address": self.end_address,
            "size": self.size,
            "is_allocated": self.is_allocated,
            "pid": self.pid,
            "process_name": self.process_name
        }

class MemoryManager:
    def __init__(self, total_size=1000, seed_initial=False):
        self.total_size = total_size
        self.seed_initial = seed_initial
        self.next_block_id = 1
        self.blocks = []
        self._init_memory()

    def _init_memory(self):
        self.blocks = [MemoryBlock(1, 0, self.total_size, False)]
        self.next_block_id = 2
        if self.seed_initial and self.total_size >= 600:
            # Seed initial sample allocations
            self.allocate("P101", 200, "First Fit", "Web Browser")
            self.allocate("P102", 300, "First Fit", "C++ Compiler")

    def allocate(self, pid, requested_size, algorithm="First Fit", process_name="User App"):
        requested_size = int(requested_size)
        if requested_size <= 0:
            raise ValueError("Requested memory size must be > 0")

        algo_norm = algorithm.lower().replace(" ", "_").replace("-", "_")
        
        target_index = -1
        
        if "first" in algo_norm:
            # First free block >= requested_size
            for i, block in enumerate(self.blocks):
                if not block.is_allocated and block.size >= requested_size:
                    target_index = i
                    break
        elif "best" in algo_norm:
            # Free block with smallest size >= requested_size
            best_size = float('inf')
            for i, block in enumerate(self.blocks):
                if not block.is_allocated and block.size >= requested_size:
                    if block.size < best_size:
                        best_size = block.size
                        target_index = i
        elif "worst" in algo_norm:
            # Free block with largest size >= requested_size
            worst_size = -1
            for i, block in enumerate(self.blocks):
                if not block.is_allocated and block.size >= requested_size:
                    if block.size > worst_size:
                        worst_size = block.size
                        target_index = i
        else:
            raise ValueError(f"Unknown allocation algorithm: {algorithm}")

        if target_index == -1:
            logger.log("MEMORY", "danger", f"Allocation failed for {pid} ({requested_size} MB). Out of memory or fragmented!")
            return {"success": False, "message": f"Memory allocation failed for {pid} ({requested_size} MB). Insufficient contiguous memory block."}

        target_block = self.blocks[target_index]
        
        # Exact fit or split block
        if target_block.size == requested_size:
            target_block.is_allocated = True
            target_block.pid = pid
            target_block.process_name = process_name
        else:
            # Split target block into allocated block and remaining free block
            allocated_block = MemoryBlock(
                self.next_block_id,
                target_block.start_address,
                requested_size,
                True,
                pid,
                process_name
            )
            self.next_block_id += 1
            
            remaining_block = MemoryBlock(
                target_block.block_id,
                target_block.start_address + requested_size,
                target_block.size - requested_size,
                False
            )
            
            self.blocks[target_index] = allocated_block
            self.blocks.insert(target_index + 1, remaining_block)

        logger.log("MEMORY", "success", f"Allocated {requested_size} MB to {pid} using {algorithm}.")
        return {"success": True, "message": f"Successfully allocated {requested_size} MB to process {pid} via {algorithm}."}

    def deallocate(self, pid_or_block_id):
        target = str(pid_or_block_id)
        deallocated = False
        
        for block in self.blocks:
            if block.is_allocated and (str(block.pid) == target or str(block.block_id) == target):
                block.is_allocated = False
                pname = block.pid
                block.pid = None
                block.process_name = None
                deallocated = True
                logger.log("MEMORY", "warning", f"Released block {block.block_id} (formerly process {pname}).")

        if deallocated:
            self._coalesce_free_blocks()
            return {"success": True, "message": f"Released memory for {target}."}
        
        return {"success": False, "message": f"No allocated memory block found matching '{target}'."}

    def _coalesce_free_blocks(self):
        """Merge adjacent free memory blocks."""
        i = 0
        while i < len(self.blocks) - 1:
            b1 = self.blocks[i]
            b2 = self.blocks[i + 1]
            if not b1.is_allocated and not b2.is_allocated:
                # Merge b2 into b1
                b1.size += b2.size
                b1.end_address = b1.start_address + b1.size
                self.blocks.pop(i + 1)
            else:
                i += 1

    def reset(self, total_size=None):
        if total_size:
            self.total_size = int(total_size)
        self._init_memory()
        logger.log("MEMORY", "info", "Memory manager reset to default state.")

    def get_metrics(self):
        allocated_size = sum(b.size for b in self.blocks if b.is_allocated)
        free_size = sum(b.size for b in self.blocks if not b.is_allocated)
        free_blocks = [b.size for b in self.blocks if not b.is_allocated]
        
        max_free_block = max(free_blocks) if free_blocks else 0
        # External fragmentation: total free space minus largest contiguous block (or sum of un-usable small free blocks)
        external_fragmentation = free_size - max_free_block if free_size > max_free_block else 0
        
        return {
            "total_memory": self.total_size,
            "used_memory": allocated_size,
            "free_memory": free_size,
            "utilization_percentage": round((allocated_size / self.total_size) * 100, 1),
            "external_fragmentation": external_fragmentation,
            "num_blocks": len(self.blocks),
            "num_free_blocks": len(free_blocks),
            "blocks": [b.to_dict() for b in self.blocks]
        }
