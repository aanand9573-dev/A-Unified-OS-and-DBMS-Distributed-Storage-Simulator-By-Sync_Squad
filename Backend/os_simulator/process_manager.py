import datetime
from backend.utils.logger import logger

VALID_STATES = ["NEW", "READY", "RUNNING", "WAITING", "TERMINATED"]

class Process:
    def __init__(self, pid, name, process_type, arrival_time, burst_time, priority=1, state="NEW", details=""):
        self.pid = str(pid)
        self.name = str(name)
        self.process_type = str(process_type) # e.g. Storage Task, Read Task, CPU Bound, etc.
        self.arrival_time = int(arrival_time)
        self.burst_time = int(burst_time)
        self.remaining_time = int(burst_time)
        self.priority = int(priority)
        self.state = state if state in VALID_STATES else "NEW"
        self.details = details
        self.created_at = datetime.datetime.now().strftime("%H:%M:%S")

    def to_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "process_type": self.process_type,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "remaining_time": self.remaining_time,
            "priority": self.priority,
            "state": self.state,
            "details": self.details,
            "created_at": self.created_at
        }

class ProcessManager:
    def __init__(self):
        self.processes = {}
        self.history = []
        self._next_pid_counter = 200
        self._init_sample_processes()

    def _init_sample_processes(self):
        """Pre-populate sample processes for immediate demonstration."""
        samples = [
            ("P101", "Web Browser", "Interactive", 0, 8, 1, "RUNNING", "User browsing session"),
            ("P102", "C++ Compiler", "CPU Bound", 1, 6, 2, "READY", "Compiling dfs_core.cpp"),
            ("P103", "Database Worker", "I/O Bound", 2, 4, 3, "WAITING", "Waiting on block disk I/O"),
            ("P104", "Background Sync", "System Task", 3, 5, 4, "READY", "Syncing node metadata"),
            ("P105", "Log Exporter", "Batch", 4, 2, 5, "TERMINATED", "Export completed")
        ]
        for pid, name, ptype, at, bt, prio, state, details in samples:
            self.processes[pid] = Process(pid, name, ptype, at, bt, prio, state, details)

    def generate_pid(self, prefix="P"):
        existing_nums = []
        for pid in list(self.processes.keys()) + [h["pid"] for h in self.history]:
            digits = "".join(c for c in pid if c.isdigit())
            if digits:
                existing_nums.append(int(digits))
        next_num = max(existing_nums, default=100) + 1
        return f"{prefix}{next_num}"

    def create_process(self, pid, name, process_type, arrival_time=0, burst_time=5, priority=1, state="NEW", details=""):
        if pid in self.processes:
            # If already exists and is terminated, replace or update
            if self.processes[pid].state == "TERMINATED":
                del self.processes[pid]
            else:
                pid = self.generate_pid()
        
        proc = Process(pid, name, process_type, arrival_time, burst_time, priority, state, details)
        self.processes[pid] = proc
        
        history_entry = {
            "pid": pid,
            "name": name,
            "process_type": process_type,
            "action": "CREATED",
            "state": state,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "details": details or f"Process {pid} started as {process_type}"
        }
        self.history.append(history_entry)
        if len(self.history) > 200:
            self.history.pop(0)

        logger.log("PROCESS", "success", f"Process {pid} ({name}) created in {state} state.")
        return proc.to_dict()

    def update_state(self, pid, new_state, details=""):
        if pid not in self.processes:
            raise KeyError(f"Process {pid} not found.")
        if new_state not in VALID_STATES:
            raise ValueError(f"Invalid state {new_state}. Valid states: {VALID_STATES}")

        old_state = self.processes[pid].state
        self.processes[pid].state = new_state
        if details:
            self.processes[pid].details = details

        history_entry = {
            "pid": pid,
            "name": self.processes[pid].name,
            "process_type": self.processes[pid].process_type,
            "action": f"{old_state} -> {new_state}",
            "state": new_state,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "details": details or f"Transitioned from {old_state} to {new_state}"
        }
        self.history.append(history_entry)
        if len(self.history) > 200:
            self.history.pop(0)

        logger.log("PROCESS", "info", f"Process {pid} transitioned: {old_state} -> {new_state}")
        return self.processes[pid].to_dict()

    def delete_process(self, pid):
        if pid in self.processes:
            proc = self.processes.pop(pid)
            self.history.append({
                "pid": pid,
                "name": proc.name,
                "process_type": proc.process_type,
                "action": "DELETED",
                "state": "REMOVED",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "details": f"Process PCB {pid} deleted from memory."
            })
            logger.log("PROCESS", "warning", f"Process {pid} ({proc.name}) removed.")
            return True
        return False

    def reset(self):
        self.processes = {}
        self.history = []
        self._init_sample_processes()
        logger.log("PROCESS", "info", "Process list reset to default sample data.")
        return [p.to_dict() for p in self.processes.values()]

    def get_all_processes(self):
        return [p.to_dict() for p in self.processes.values()]

    def get_history(self, limit=50):
        return list(reversed(self.history[-limit:]))

    def get_summary(self):
        counts = {s: 0 for s in VALID_STATES}
        for p in self.processes.values():
            counts[p.state] += 1
        
        running_proc = next((p.to_dict() for p in self.processes.values() if p.state == "RUNNING"), None)
        ready_queue = [p.to_dict() for p in self.processes.values() if p.state == "READY"]
        
        return {
            "total": len(self.processes),
            "running": counts["RUNNING"],
            "ready": counts["READY"],
            "waiting": counts["WAITING"],
            "terminated": counts["TERMINATED"],
            "new": counts["NEW"],
            "state_counts": counts,
            "running_process": running_proc,
            "ready_queue": ready_queue,
            "history_count": len(self.history)
        }
