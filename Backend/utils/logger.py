import datetime
import threading

class SystemLogger:
    """
    Thread-safe in-memory activity logger for the OS Simulator.
    Logs system actions, algorithm executions, state transitions, and memory operations.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SystemLogger, cls).__new__(cls)
                cls._instance.logs = []
                cls._instance.max_logs = 200
                cls._instance._init_default_logs()
            return cls._instance

    def _init_default_logs(self):
        now = datetime.datetime.now()
        t = lambda seconds_ago: (now - datetime.timedelta(seconds=seconds_ago)).strftime("%H:%M:%S")
        
        self.logs = [
            {"id": 1, "timestamp": t(30), "module": "SYSTEM", "level": "info", "message": "OS Simulator engine initialized successfully."},
            {"id": 2, "timestamp": t(25), "module": "PROCESS", "level": "success", "message": "Sample processes (P101, P102, P103, P104) created."},
            {"id": 3, "timestamp": t(20), "module": "MEMORY", "level": "info", "message": "Simulated RAM initialized with 1000 MB capacity."},
            {"id": 4, "timestamp": t(15), "module": "MEMORY", "level": "success", "message": "Allocated 200 MB to process P101 using First Fit."},
            {"id": 5, "timestamp": t(10), "module": "CPU", "level": "info", "message": "FCFS Scheduling simulation ready with 4 processes."},
            {"id": 6, "timestamp": t(5), "module": "DEADLOCK", "level": "success", "message": "Banker's algorithm verified initial state as SAFE."}
        ]

    def log(self, module: str, level: str, message: str):
        """
        Add a log entry.
        module: PROCESS, CPU, MEMORY, DISK, DEADLOCK, SYNCHRONIZATION, SYSTEM
        level: info, success, warning, danger
        """
        with self._lock:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_id = len(self.logs) + 1
            entry = {
                "id": log_id,
                "timestamp": timestamp,
                "module": module.upper(),
                "level": level.lower(),
                "message": message
            }
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs.pop(0)
            return entry

    def get_logs(self, limit=50, module_filter=None):
        with self._lock:
            filtered = self.logs
            if module_filter and module_filter.upper() != "ALL":
                filtered = [l for l in filtered if l["module"] == module_filter.upper()]
            return list(reversed(filtered[-limit:]))

    def clear(self):
        with self._lock:
            self.logs = []
            self.log("SYSTEM", "info", "System activity logs cleared.")

logger = SystemLogger()
