"""
Concurrency Synchronization Module
Provides thread-safe locks and semaphores for real backend operations:
1. FileLockManager: Fine-grained per-file reentrant locks to serialize writes, renames, and deletions
   on the same file while allowing concurrent operations across different files.
2. NodeSemaphoreManager: Per-storage-node bounded semaphores to throttle concurrent I/O threads
   accessing the same node folder.
3. AllocationLock: Process lock ensuring atomic node selection and capacity reservations across concurrent uploads.
"""

import threading
from contextlib import contextmanager
from backend.utils.logger import logger

class FileLockManager:
    """
    Manages per-file locks so concurrent operations on different files run simultaneously,
    while conflicting operations on the same file are safely serialized without race conditions.
    """
    def __init__(self):
        self._locks = {}
        self._meta_lock = threading.Lock()

    def _get_lock(self, file_id_or_name):
        key = str(file_id_or_name)
        with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    @contextmanager
    def acquire(self, file_id_or_name, op_name="Operation"):
        lock = self._get_lock(file_id_or_name)
        acquired = lock.acquire()
        try:
            yield
        finally:
            if acquired:
                lock.release()

    def cleanup(self, file_id_or_name):
        key = str(file_id_or_name)
        with self._meta_lock:
            self._locks.pop(key, None)


class NodeSemaphoreManager:
    """
    Per-node bounded semaphores to prevent I/O congestion and race conditions
    when multiple worker threads write or read blocks from the same node folder.
    """
    def __init__(self, max_concurrent_per_node=4):
        self.max_concurrent = max_concurrent_per_node
        self._semaphores = {}
        self._meta_lock = threading.Lock()

    def _get_semaphore(self, node_id):
        key = str(node_id)
        with self._meta_lock:
            if key not in self._semaphores:
                self._semaphores[key] = threading.BoundedSemaphore(self.max_concurrent)
            return self._semaphores[key]

    @contextmanager
    def acquire(self, node_id):
        sem = self._get_semaphore(node_id)
        sem.acquire()
        try:
            yield
        finally:
            sem.release()


# Global singletons
file_lock_manager = FileLockManager()
node_semaphore_manager = NodeSemaphoreManager(max_concurrent_per_node=4)
allocation_lock = threading.Lock()
