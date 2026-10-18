"""
Simulator State Model
Centralized in-memory state store for the OS Simulator system.
Can be persisted to JSON or migrated to MySQL database in Phase 2.
"""

from backend.os_simulator.process_manager import ProcessManager
from backend.os_simulator.memory_manager import MemoryManager
from backend.os_simulator.deadlock_manager import DeadlockManager
from backend.os_simulator.synchronization import MutexSimulator, SemaphoreSimulator

class SimulatorState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimulatorState, cls).__new__(cls)
            cls._instance.process_manager = ProcessManager()
            cls._instance.memory_manager = MemoryManager(total_size=1000, seed_initial=True)
            cls._instance.deadlock_manager = DeadlockManager()
            cls._instance.mutex_sim = MutexSimulator("Shared Database Buffer")
            cls._instance.semaphore_sim = SemaphoreSimulator("Shared Resource Pool", max_permits=2)
            cls._instance.disk_state = {
                "initial_head": 50,
                "requests": [10, 90, 35, 70, 20],
                "direction": "right",
                "disk_size": 200
            }
        return cls._instance

    def reset_all(self):
        self.process_manager.reset()
        self.memory_manager.reset()
        self.deadlock_manager.reset()
        self.mutex_sim.reset()
        self.semaphore_sim.reset()
        self.disk_state = {
            "initial_head": 50,
            "requests": [10, 90, 35, 70, 20],
            "direction": "right",
            "disk_size": 200
        }

simulator_state = SimulatorState()
