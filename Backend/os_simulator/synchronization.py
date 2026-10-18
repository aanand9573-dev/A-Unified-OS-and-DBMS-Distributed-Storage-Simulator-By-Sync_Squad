"""
Process Synchronization Simulator Module
Educational simulations of:
1. Mutex (Binary Lock)
2. Semaphore (Counting Semaphore)

Simulates critical section concurrency access and lock ownership transitions.
"""

import threading
from backend.utils.logger import logger

class MutexSimulator:
    def __init__(self, resource_name="Shared Database Buffer"):
        self.resource_name = resource_name
        self.is_locked = False
        self.owner_pid = None
        self.waiting_queue = []
        self.history = []
        self._thread_lock = threading.Lock()

    def acquire(self, pid):
        pid = str(pid)
        with self._thread_lock:
            if not self.is_locked:
                self.is_locked = True
                self.owner_pid = pid
                msg = f"{pid} -> LOCK ACQUIRED on {self.resource_name}"
                self.history.append(msg)
                logger.log("SYNCHRONIZATION", "success", msg)
                return {"success": True, "status": "ACQUIRED", "message": msg, "state": self.to_dict()}
            else:
                if pid == self.owner_pid:
                    return {"success": False, "status": "ALREADY_OWNER", "message": f"{pid} already owns the lock.", "state": self.to_dict()}
                if pid not in self.waiting_queue:
                    self.waiting_queue.append(pid)
                msg = f"{pid} -> WAITING in queue for {self.resource_name}"
                self.history.append(msg)
                logger.log("SYNCHRONIZATION", "warning", msg)
                return {"success": True, "status": "WAITING", "message": msg, "state": self.to_dict()}

    def release(self, pid):
        pid = str(pid)
        with self._thread_lock:
            if not self.is_locked or self.owner_pid != pid:
                if pid in self.waiting_queue:
                    self.waiting_queue.remove(pid)
                msg = f"Release failed: {pid} does not hold the lock on {self.resource_name}."
                logger.log("SYNCHRONIZATION", "danger", msg)
                return {"success": False, "status": "ERROR", "message": msg, "state": self.to_dict()}

            msg1 = f"{pid} -> LOCK RELEASED on {self.resource_name}"
            self.history.append(msg1)
            logger.log("SYNCHRONIZATION", "info", msg1)

            if self.waiting_queue:
                next_pid = self.waiting_queue.pop(0)
                self.owner_pid = next_pid
                self.is_locked = True
                msg2 = f"{next_pid} -> LOCK ACQUIRED (granted from waiting queue)"
                self.history.append(msg2)
                logger.log("SYNCHRONIZATION", "success", msg2)
            else:
                self.is_locked = False
                self.owner_pid = None

            return {"success": True, "status": "RELEASED", "message": msg1, "state": self.to_dict()}

    def reset(self):
        with self._thread_lock:
            self.is_locked = False
            self.owner_pid = None
            self.waiting_queue = []
            self.history = []
            logger.log("SYNCHRONIZATION", "info", "Mutex lock reset.")

    def to_dict(self):
        return {
            "resource_name": self.resource_name,
            "is_locked": self.is_locked,
            "owner_pid": self.owner_pid,
            "waiting_queue": list(self.waiting_queue),
            "history": self.history[-10:]
        }


class SemaphoreSimulator:
    def __init__(self, resource_name="Shared Printer Service", max_permits=2):
        self.resource_name = resource_name
        self.max_permits = max_permits
        self.current_permits = max_permits
        self.active_processes = []
        self.waiting_queue = []
        self.history = []
        self._thread_lock = threading.Lock()

    def wait(self, pid):
        """P() / wait() operation."""
        pid = str(pid)
        with self._thread_lock:
            if self.current_permits > 0:
                self.current_permits -= 1
                if pid not in self.active_processes:
                    self.active_processes.append(pid)
                msg = f"{pid} -> SEMAPHORE PERMIT GRANTED (Remaining permits: {self.current_permits})"
                self.history.append(msg)
                logger.log("SYNCHRONIZATION", "success", msg)
                return {"success": True, "status": "GRANTED", "message": msg, "state": self.to_dict()}
            else:
                if pid not in self.waiting_queue and pid not in self.active_processes:
                    self.waiting_queue.append(pid)
                msg = f"{pid} -> SEMAPHORE BLOCKED / WAITING (No permits left)"
                self.history.append(msg)
                logger.log("SYNCHRONIZATION", "warning", msg)
                return {"success": True, "status": "BLOCKED", "message": msg, "state": self.to_dict()}

    def signal(self, pid=None):
        """V() / signal() operation."""
        with self._thread_lock:
            if self.active_processes:
                releasing_pid = pid if (pid and pid in self.active_processes) else self.active_processes.pop(0)
                if releasing_pid in self.active_processes:
                    self.active_processes.remove(releasing_pid)

                msg1 = f"{releasing_pid} -> SIGNAL RELEASED permit"
                self.history.append(msg1)
                logger.log("SYNCHRONIZATION", "info", msg1)

                if self.waiting_queue:
                    next_pid = self.waiting_queue.pop(0)
                    self.active_processes.append(next_pid)
                    msg2 = f"{next_pid} -> PROMOTED from waiting queue to active"
                    self.history.append(msg2)
                    logger.log("SYNCHRONIZATION", "success", msg2)
                else:
                    self.current_permits = min(self.max_permits, self.current_permits + 1)
                return {"success": True, "status": "RELEASED", "message": msg1, "state": self.to_dict()}
            else:
                if self.current_permits < self.max_permits:
                    self.current_permits += 1
                return {"success": True, "status": "SIGNAL_IDLE", "message": "Signal executed on idle semaphore.", "state": self.to_dict()}

    def reset(self, max_permits=None):
        with self._thread_lock:
            if max_permits:
                self.max_permits = int(max_permits)
            self.current_permits = self.max_permits
            self.active_processes = []
            self.waiting_queue = []
            self.history = []
            logger.log("SYNCHRONIZATION", "info", f"Semaphore reset (Max permits: {self.max_permits}).")

    def to_dict(self):
        return {
            "resource_name": self.resource_name,
            "max_permits": self.max_permits,
            "current_permits": self.current_permits,
            "active_processes": list(self.active_processes),
            "waiting_queue": list(self.waiting_queue),
            "history": self.history[-10:]
        }
