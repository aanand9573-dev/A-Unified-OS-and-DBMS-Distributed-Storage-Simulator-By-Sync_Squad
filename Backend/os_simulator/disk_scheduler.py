"""
Disk Scheduler Module
Implements disk scheduling algorithms:
1. FCFS (First Come First Served)
2. SSTF (Shortest Seek Time First)
3. SCAN (Elevator Algorithm)

Calculates scheduled sequence, head movement steps, total seek count, and average seek distance.
Also provides SharedDiskScheduler: a live shared request queue routing real DFS block
reads and writes through configurable disk scheduling algorithms, clearly distinguishing
simulated disk-head metrics from physical host I/O operations.
"""

import time
import hashlib
import threading
from collections import deque
from backend.utils.logger import logger

def fcfs_disk(initial_head, requests):
    """
    FCFS Disk Scheduling.
    Services requests in the exact order they arrive.
    """
    head = int(initial_head)
    reqs = [int(r) for r in requests]
    
    sequence = [head]
    steps = []
    total_movement = 0
    
    curr = head
    for r in reqs:
        dist = abs(r - curr)
        total_movement += dist
        steps.append({
            "from_pos": curr,
            "to_pos": r,
            "distance": dist
        })
        sequence.append(r)
        curr = r
        
    avg_movement = round(total_movement / len(reqs), 2) if reqs else 0
    return _compile_disk_result("FCFS", head, reqs, sequence, steps, total_movement, avg_movement)


def sstf_disk(initial_head, requests):
    """
    SSTF Disk Scheduling.
    Services the request closest to the current head position.
    """
    head = int(initial_head)
    pending = [int(r) for r in requests]
    
    sequence = [head]
    steps = []
    total_movement = 0
    
    curr = head
    while pending:
        closest_idx = 0
        min_dist = abs(pending[0] - curr)
        
        for i in range(1, len(pending)):
            dist = abs(pending[i] - curr)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
                
        r = pending.pop(closest_idx)
        total_movement += min_dist
        steps.append({
            "from_pos": curr,
            "to_pos": r,
            "distance": min_dist
        })
        sequence.append(r)
        curr = r
        
    avg_movement = round(total_movement / len(requests), 2) if requests else 0
    return _compile_disk_result("SSTF", head, requests, sequence, steps, total_movement, avg_movement)


def scan_disk(initial_head, requests, direction="right", disk_size=200):
    """
    SCAN Disk Scheduling (Elevator Algorithm).
    Moves towards specified direction (left towards 0, or right towards disk_size-1),
    servicing requests, then reverses direction.
    """
    head = int(initial_head)
    reqs = [int(r) for r in requests]
    disk_max = disk_size - 1
    direction = str(direction).lower()
    
    left = [r for r in reqs if r < head]
    right = [r for r in reqs if r >= head]
    
    left.sort(reverse=True) # Descending for moving left
    right.sort()           # Ascending for moving right
    
    sequence = [head]
    steps = []
    total_movement = 0
    curr = head
    
    if direction == "left":
        run = left + ([0] if right else []) + right
    else:
        run = right + ([disk_max] if left else []) + left

    seek_targets = []
    for pos in run:
        if pos not in seek_targets and pos != head:
            seek_targets.append(pos)
            
    for r in seek_targets:
        dist = abs(r - curr)
        total_movement += dist
        steps.append({
            "from_pos": curr,
            "to_pos": r,
            "distance": dist
        })
        sequence.append(r)
        curr = r
        
    avg_movement = round(total_movement / len(reqs), 2) if reqs else 0
    return _compile_disk_result(f"SCAN ({direction.upper()})", head, reqs, sequence, steps, total_movement, avg_movement)


def compare_all_disk(initial_head, requests, direction="right", disk_size=200):
    res_fcfs = fcfs_disk(initial_head, requests)
    res_sstf = sstf_disk(initial_head, requests)
    res_scan = scan_disk(initial_head, requests, direction, disk_size)
    
    comparison = [
        {"algorithm": "FCFS", "total_movement": res_fcfs["total_movement"], "avg_movement": res_fcfs["avg_movement"]},
        {"algorithm": "SSTF", "total_movement": res_sstf["total_movement"], "avg_movement": res_sstf["avg_movement"]},
        {"algorithm": f"SCAN ({direction.upper()})", "total_movement": res_scan["total_movement"], "avg_movement": res_scan["avg_movement"]}
    ]
    
    best_algo = min(comparison, key=lambda x: x["total_movement"])["algorithm"]
    
    return {
        "initial_head": initial_head,
        "requests": requests,
        "comparison": comparison,
        "best_algorithm": best_algo,
        "details": {
            "FCFS": res_fcfs,
            "SSTF": res_sstf,
            "SCAN": res_scan
        }
    }


def _compile_disk_result(algo_name, initial_head, requests, sequence, steps, total_movement, avg_movement):
    res = {
        "algorithm": algo_name,
        "initial_head": initial_head,
        "requests": requests,
        "scheduled_sequence": sequence,
        "steps": steps,
        "total_movement": total_movement,
        "avg_movement": avg_movement
    }
    logger.log("DISK", "success", f"Executed {algo_name}. Total head movement: {total_movement} cylinders (Avg: {avg_movement}).")
    return res


# =========================================================================
# SHARED DISK SCHEDULER: INTEGRATED LIVE I/O REQUEST QUEUE
# =========================================================================

class SharedDiskScheduler:
    """
    Shared thread-safe Disk Scheduler routing actual block reads and writes.
    Maintains a shared request queue and dispatches I/O according to active algorithm
    (FCFS, SSTF, SCAN).
    Clearly distinguishes:
    1. Simulated Disk Metrics: Cylinder/track positions (0-199), simulated head movements,
       seek distances, and seek order.
    2. Physical Disk Operations: Actual bytes written/read, host file paths, elapsed host
       I/O latency in milliseconds, and status.
    """

    SUPPORTED_ALGORITHMS = ["FCFS", "SSTF", "SCAN"]

    def __init__(self, disk_size=200, initial_head=50, default_algo="FCFS"):
        self.disk_size = disk_size
        self.current_head = int(initial_head)
        self.active_algorithm = default_algo.upper() if default_algo.upper() in self.SUPPORTED_ALGORITHMS else "FCFS"
        self.direction = "right"  # 'right' (towards disk_size-1) or 'left' (towards 0)
        self.request_queue = []   # List of pending I/O dicts
        self.history = deque(maxlen=100) # List of recently completed I/O records
        self.total_seek_cylinders = 0
        self.total_requests_serviced = 0
        self._counter = 0
        self._lock = threading.Lock()
        self._dispatch_lock = threading.Lock()

    def set_algorithm(self, algo_name, direction=None):
        with self._lock:
            algo_upper = str(algo_name).upper().strip()
            if algo_upper not in self.SUPPORTED_ALGORITHMS:
                raise ValueError(f"Unsupported algorithm '{algo_name}'. Choose from: {self.SUPPORTED_ALGORITHMS}")
            self.active_algorithm = algo_upper
            if direction in ["right", "left"]:
                self.direction = direction
            logger.log("DISK", "info", f"Shared Disk Scheduler algorithm changed to {self.active_algorithm} (direction={self.direction}).")
            return {
                "algorithm": self.active_algorithm,
                "direction": self.direction,
                "current_head": self.current_head
            }

    def get_algorithm(self):
        with self._lock:
            return {
                "active_algorithm": self.active_algorithm,
                "direction": self.direction,
                "current_head": self.current_head,
                "supported": self.SUPPORTED_ALGORITHMS
            }

    @staticmethod
    def calculate_block_cylinder(block_id, disk_size=200):
        """
        Deterministically maps a block identifier to a simulated disk cylinder track (0 to disk_size - 1).
        Uses stable MD5 hash integer conversion.
        """
        h = hashlib.md5(str(block_id).encode("utf-8")).hexdigest()
        track = int(h, 16) % disk_size
        return track

    def _select_next_request_index(self):
        """Selects the index of the next request in self.request_queue based on active algorithm."""
        if not self.request_queue:
            return 0

        if self.active_algorithm == "FCFS":
            return 0

        elif self.active_algorithm == "SSTF":
            best_idx = 0
            best_dist = abs(self.request_queue[0]["target_cylinder"] - self.current_head)
            for i, r in enumerate(self.request_queue):
                dist = abs(r["target_cylinder"] - self.current_head)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            return best_idx

        elif self.active_algorithm == "SCAN":
            if self.direction == "right":
                candidates = [(i, r) for i, r in enumerate(self.request_queue) if r["target_cylinder"] >= self.current_head]
                if candidates:
                    candidates.sort(key=lambda item: item[1]["target_cylinder"])
                    return candidates[0][0]
                else:
                    self.direction = "left"
                    candidates = [(i, r) for i, r in enumerate(self.request_queue) if r["target_cylinder"] < self.current_head]
                    if candidates:
                        candidates.sort(key=lambda item: item[1]["target_cylinder"], reverse=True)
                        return candidates[0][0]
                    return 0
            else:  # left
                candidates = [(i, r) for i, r in enumerate(self.request_queue) if r["target_cylinder"] <= self.current_head]
                if candidates:
                    candidates.sort(key=lambda item: item[1]["target_cylinder"], reverse=True)
                    return candidates[0][0]
                else:
                    self.direction = "right"
                    candidates = [(i, r) for i, r in enumerate(self.request_queue) if r["target_cylinder"] > self.current_head]
                    if candidates:
                        candidates.sort(key=lambda item: item[1]["target_cylinder"])
                        return candidates[0][0]
                    return 0
        return 0

    def execute_block_io(self, block_id, op_type, file_path, io_worker_fn):
        """
        Enqueues an I/O request into the shared queue, schedules it according to the
        active algorithm, dispatches the real physical I/O operation, and records
        both simulated head movement and physical host disk metrics.
        """
        target_cylinder = self.calculate_block_cylinder(block_id, self.disk_size)

        req = {
            "id": None,
            "block_id": block_id,
            "op_type": op_type.upper(),
            "file_path": file_path,
            "target_cylinder": target_cylinder,
            "timestamp": time.strftime("%H:%M:%S"),
            "worker_fn": io_worker_fn,
            "done_event": threading.Event(),
            "result": None,
            "error": None,
            "done": False
        }

        with self._lock:
            self._counter += 1
            req["id"] = f"IO-{self._counter:04d}"
            self.request_queue.append(req)

        while not req["done"]:
            with self._dispatch_lock:
                if req["done"]:
                    break

                with self._lock:
                    if not self.request_queue:
                        break
                    idx = self._select_next_request_index()
                    cur_req = self.request_queue.pop(idx)
                    prev_head = self.current_head
                    next_head = cur_req["target_cylinder"]
                    seek_dist = abs(next_head - prev_head)
                    self.current_head = next_head
                    self.total_seek_cylinders += seek_dist
                    self.total_requests_serviced += 1
                    avg_seek = round(self.total_seek_cylinders / self.total_requests_serviced, 2)
                    used_algo = self.active_algorithm

                t0 = time.perf_counter()
                physical_status = "SUCCESS"
                bytes_transferred = 0
                error_msg = None
                try:
                    res = cur_req["worker_fn"]()
                    cur_req["result"] = res
                    if isinstance(res, (bytes, bytearray)):
                        bytes_transferred = len(res)
                    elif isinstance(res, int):
                        bytes_transferred = res
                except Exception as ex:
                    physical_status = "ERROR"
                    error_msg = str(ex)
                    cur_req["error"] = ex
                finally:
                    t1 = time.perf_counter()
                    physical_ms = round((t1 - t0) * 1000, 3)

                    event_record = {
                        "id": cur_req["id"],
                        "timestamp": cur_req["timestamp"],
                        "block_id": cur_req["block_id"],
                        "op_type": cur_req["op_type"],
                        "simulated_metrics": {
                            "algorithm": used_algo,
                            "target_cylinder": next_head,
                            "prev_head_cylinder": prev_head,
                            "new_head_cylinder": next_head,
                            "seek_distance_cylinders": seek_dist,
                            "cumulative_seeks": self.total_seek_cylinders,
                            "avg_seek_cylinders": avg_seek
                        },
                        "physical_operation": {
                            "file_path": cur_req["file_path"],
                            "bytes_transferred": bytes_transferred,
                            "host_latency_ms": physical_ms,
                            "status": physical_status,
                            "error": error_msg
                        }
                    }
                    with self._lock:
                        self.history.appendleft(event_record)

                    cur_req["done"] = True
                    cur_req["done_event"].set()

                    logger.log(
                        "DISK",
                        "success" if physical_status == "SUCCESS" else "danger",
                        f"[{used_algo}] {cur_req['op_type']} {cur_req['block_id']} @ Track {next_head} "
                        f"(Seek: {seek_dist} cyl, Host I/O: {physical_ms}ms, {physical_status})"
                    )

            if not req["done"]:
                req["done_event"].wait(timeout=0.01)

        if req["error"]:
            raise req["error"]
        return req["result"]

    def get_queue_and_metrics(self):
        with self._lock:
            avg_seek = round(self.total_seek_cylinders / self.total_requests_serviced, 2) if self.total_requests_serviced > 0 else 0.0
            serialized_queue = [
                {
                    "id": r["id"],
                    "block_id": r["block_id"],
                    "op_type": r["op_type"],
                    "target_cylinder": r["target_cylinder"],
                    "file_path": r.get("file_path", ""),
                    "timestamp": r["timestamp"]
                }
                for r in self.request_queue
            ]
            return {
                "active_algorithm": self.active_algorithm,
                "direction": self.direction,
                "current_head": self.current_head,
                "disk_size": self.disk_size,
                "pending_queue_count": len(self.request_queue),
                "pending_queue": serialized_queue,
                "total_requests_serviced": self.total_requests_serviced,
                "total_seek_cylinders": self.total_seek_cylinders,
                "avg_seek_cylinders": avg_seek,
                "recent_history": list(self.history)
            }

    def clear_metrics(self):
        with self._lock:
            self.total_seek_cylinders = 0
            self.total_requests_serviced = 0
            self.history.clear()
            self.request_queue.clear()
            logger.log("DISK", "info", "Shared Disk Scheduler queue and metrics reset.")


# Singleton instance
shared_disk_scheduler = SharedDiskScheduler()
