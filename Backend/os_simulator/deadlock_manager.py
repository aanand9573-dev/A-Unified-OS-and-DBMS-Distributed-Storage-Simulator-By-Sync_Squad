"""
Deadlock Manager Module
Implements:
1. Banker's Algorithm for Deadlock Avoidance (Safe State Check & Resource Request Validation)
2. Deadlock Detection algorithm based on Wait-For Graph / Allocation-Request verification.

Calculates Need Matrix, Safe Sequence, and step-by-step vector states.
"""

from backend.utils.logger import logger

class DeadlockManager:
    def __init__(self):
        self._init_default_data()

    def _init_default_data(self):
        """Pre-populate classic standard Banker's algorithm sample case for quick demo."""
        self.process_names = ["P0", "P1", "P2", "P3", "P4"]
        self.resource_names = ["R1 (CPU)", "R2 (Memory)", "R3 (I/O)"]
        self.available = [3, 3, 2]
        
        self.allocation = [
            [0, 1, 0], # P0
            [2, 0, 0], # P1
            [3, 0, 2], # P2
            [2, 1, 1], # P3
            [0, 0, 2]  # P4
        ]
        
        self.max_matrix = [
            [7, 5, 3], # P0
            [3, 2, 2], # P1
            [9, 0, 2], # P2
            [2, 2, 2], # P3
            [4, 3, 3]  # P4
        ]
        
        self.need_matrix = self.calculate_need_matrix(self.allocation, self.max_matrix)

    def calculate_need_matrix(self, allocation, max_matrix):
        need = []
        for i in range(len(allocation)):
            row = []
            for j in range(len(allocation[i])):
                val = max(0, max_matrix[i][j] - allocation[i][j])
                row.append(val)
            need.append(row)
        return need

    def set_matrices(self, process_names, resource_names, available, allocation, max_matrix):
        self.process_names = [str(p) for p in process_names]
        self.resource_names = [str(r) for r in resource_names]
        self.available = [int(a) for a in available]
        self.allocation = [[int(x) for x in row] for row in allocation]
        self.max_matrix = [[int(x) for x in row] for row in max_matrix]
        self.need_matrix = self.calculate_need_matrix(self.allocation, self.max_matrix)
        logger.log("DEADLOCK", "info", f"Updated Deadlock matrices for {len(self.process_names)} processes.")

    def check_safe_state(self):
        """
        Executes Banker's Algorithm to find if system is in a Safe State and return Safe Sequence.
        """
        n_proc = len(self.process_names)
        n_res = len(self.resource_names)
        
        work = list(self.available)
        finish = [False] * n_proc
        safe_sequence = []
        execution_steps = []
        
        count = 0
        while count < n_proc:
            found_candidate = False
            
            for i in range(n_proc):
                if not finish[i]:
                    # Check if Need[i] <= Work
                    can_execute = True
                    for j in range(n_res):
                        if self.need_matrix[i][j] > work[j]:
                            can_execute = False
                            break
                            
                    if can_execute:
                        prev_work = list(work)
                        # Process i executes and releases its allocated resources back to Work
                        for j in range(n_res):
                            work[j] += self.allocation[i][j]
                            
                        finish[i] = True
                        safe_sequence.append(self.process_names[i])
                        found_candidate = True
                        count += 1
                        
                        execution_steps.append({
                            "step": count,
                            "process": self.process_names[i],
                            "prev_work": prev_work,
                            "need": self.need_matrix[i],
                            "allocation": self.allocation[i],
                            "new_work": list(work)
                        })
                        break
                        
            if not found_candidate:
                # System is in UNSAFE state / Deadlock prone!
                deadlocked_procs = [self.process_names[i] for i in range(n_proc) if not finish[i]]
                logger.log("DEADLOCK", "danger", f"UNSAFE STATE DETECTED! Deadlocked candidate processes: {deadlocked_procs}")
                return {
                    "is_safe": False,
                    "status": "UNSAFE / DEADLOCK DETECTED",
                    "deadlocked_processes": deadlocked_procs,
                    "safe_sequence": [],
                    "execution_steps": execution_steps,
                    "available": self.available,
                    "allocation": self.allocation,
                    "max_matrix": self.max_matrix,
                    "need_matrix": self.need_matrix,
                    "process_names": self.process_names,
                    "resource_names": self.resource_names
                }

        logger.log("DEADLOCK", "success", f"SAFE STATE! Safe sequence found: {' -> '.join(safe_sequence)}")
        return {
            "is_safe": True,
            "status": "SAFE STATE",
            "safe_sequence": safe_sequence,
            "execution_steps": execution_steps,
            "available": self.available,
            "allocation": self.allocation,
            "max_matrix": self.max_matrix,
            "need_matrix": self.need_matrix,
            "process_names": self.process_names,
            "resource_names": self.resource_names
        }

    def request_resources(self, pid, request_vector):
        """
        Banker's Resource-Request Algorithm:
        Simulate granting request to process PID if Request <= Need and Request <= Available, and system remains Safe.
        """
        if pid not in self.process_names:
            return {"granted": False, "message": f"Process {pid} not found."}
            
        p_idx = self.process_names.index(pid)
        req = [int(x) for x in request_vector]
        n_res = len(self.resource_names)
        
        # 1. Check Request <= Need
        for j in range(n_res):
            if req[j] > self.need_matrix[p_idx][j]:
                return {"granted": False, "message": f"Error: Process {pid} requested more than its declared max need for resource {self.resource_names[j]}."}

        # 2. Check Request <= Available
        for j in range(n_res):
            if req[j] > self.available[j]:
                logger.log("DEADLOCK", "warning", f"Resource request by {pid} exceeds available resources. Process must wait.")
                return {"granted": False, "message": f"Process {pid} must wait! Insufficient available resources for request {req}."}

        # 3. Pretend to allocate resources
        saved_avail = list(self.available)
        saved_alloc = [list(row) for row in self.allocation]
        saved_need = [list(row) for row in self.need_matrix]
        
        for j in range(n_res):
            self.available[j] -= req[j]
            self.allocation[p_idx][j] += req[j]
            self.need_matrix[p_idx][j] -= req[j]
            
        safety_check = self.check_safe_state()
        
        if safety_check["is_safe"]:
            logger.log("DEADLOCK", "success", f"Resource request {req} by {pid} GRANTED safely!")
            return {
                "granted": True,
                "message": f"Resource request {req} for process {pid} GRANTED safely!",
                "safety_check": safety_check
            }
        else:
            # Rollback
            self.available = saved_avail
            self.allocation = saved_alloc
            self.need_matrix = saved_need
            logger.log("DEADLOCK", "danger", f"Resource request {req} by {pid} DENIED to prevent unsafe deadlock state!")
            return {
                "granted": False,
                "message": f"Resource request {req} for process {pid} DENIED because it leads to an UNSAFE deadlock state.",
                "safety_check": safety_check
            }

    def reset(self):
        self._init_default_data()
        logger.log("DEADLOCK", "info", "Reset Deadlock Manager matrices to default state.")
