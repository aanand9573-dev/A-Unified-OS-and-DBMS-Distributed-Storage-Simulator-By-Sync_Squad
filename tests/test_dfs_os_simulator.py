"""
Comprehensive Test Suite for Distributed File System & OS Simulator
Validates:
1. File splitting into binary blocks & physical node storage
2. Block placement, capacity accounting, metadata persistence
3. 2-way block replication across distinct storage nodes
4. File download & reconstruction with MD5 checksum verification
5. Multiple file formats (Text, Binary ZIP, PDF simulation, Empty file)
6. Primary node failure & replica failover download
7. Corrupted block detection, replica failover, and self-healing
8. Node capacity exhaustion handling & rollback
9. All nodes offline error handling
10. File renaming & recursive directory deletion
11. OS Process Manager lifecycle, PID generation, and process history
12. CPU Schedulers (FCFS, Round Robin, Priority, SJF)
13. Memory Management (First Fit, Best Fit, Worst Fit, fragmentation, coalescing)
14. Disk Schedulers (FCFS, SSTF, SCAN)
15. Banker's Deadlock Algorithm & Resource Request
16. Synchronization Mutex & Counting Semaphore
17. Full Flask API Endpoints Integration
"""

import os
import sys
import unittest
import hashlib
import json
import io

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.models.metadata_store import metadata_store
from backend.models.simulator_state import simulator_state
from backend.dfs.file_manager import file_manager
from backend.dfs.node_manager import node_manager
from backend.dfs.block_manager import block_manager
from backend.dfs.replication import replication_manager
from backend.dfs.recovery import recovery_manager

from backend.os_simulator.cpu_scheduler import (
    fcfs_schedule, round_robin_schedule, priority_schedule, sjf_schedule
)
from backend.os_simulator.disk_scheduler import (
    fcfs_disk, sstf_disk, scan_disk, compare_all_disk
)
from backend.os_simulator.memory_manager import MemoryManager
from backend.os_simulator.deadlock_manager import DeadlockManager
from backend.os_simulator.synchronization import MutexSimulator, SemaphoreSimulator

class TestDfsOsSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def setUp(self):
        # Reset state cleanly before each test
        metadata_store.reset()
        simulator_state.reset_all()

    # =========================================================
    # 1. DFS REAL FILE SPLITTING, STORAGE, AND RECONSTRUCTION
    # =========================================================
    def test_upload_split_and_reconstruct_text(self):
        content = ("Distributed File System Test Content.\n" * 1000).encode("utf-8")
        original_hash = hashlib.md5(content).hexdigest()

        meta = file_manager.upload_file("test_doc.txt", content, block_size_mb=1)
        self.assertIn("id", meta)
        self.assertEqual(meta["name"], "test_doc.txt")
        self.assertGreater(meta["total_blocks"], 0)
        self.assertEqual(meta["checksum"], original_hash)

        # Verify blocks exist physically on node directories
        for b_id in meta["block_ids"]:
            b_meta = metadata_store.blocks[b_id]
            self.assertTrue(os.path.exists(b_meta["primary_file_path"]))
            self.assertTrue(os.path.exists(b_meta["replica_file_path"]))
            self.assertNotEqual(b_meta["primary_node_id"], b_meta["replica_node_id"])

        # Reconstruct and compare bytes and hash
        reconstructed_bytes, filename = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(filename, "test_doc.txt")
        self.assertEqual(hashlib.md5(reconstructed_bytes).hexdigest(), original_hash)
        self.assertEqual(reconstructed_bytes, content)

    def test_upload_binary_and_pdf_formats(self):
        # Binary simulated PDF bytes (starts with %PDF-1.5 header)
        pdf_bytes = b"%PDF-1.5 " + os.urandom(250000) + b" %%EOF"
        original_hash = hashlib.md5(pdf_bytes).hexdigest()

        meta = file_manager.upload_file("sample_report.pdf", pdf_bytes, block_size_mb=1)
        reconstructed_bytes, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(hashlib.md5(reconstructed_bytes).hexdigest(), original_hash)

        # Binary simulated ZIP bytes (starts with PK\x03\x04 header)
        zip_bytes = b"PK\x03\x04" + os.urandom(150000)
        zip_hash = hashlib.md5(zip_bytes).hexdigest()
        meta_zip = file_manager.upload_file("archive.zip", zip_bytes, block_size_mb=1)
        reconstructed_zip, _ = file_manager.download_and_reconstruct_file(meta_zip["id"])
        self.assertEqual(hashlib.md5(reconstructed_zip).hexdigest(), zip_hash)

    def test_empty_file_handling(self):
        empty_bytes = b""
        meta = file_manager.upload_file("empty.txt", empty_bytes, block_size_mb=1)
        self.assertEqual(meta["size_bytes"], 0)
        self.assertEqual(meta["total_blocks"], 1)

        reconstructed_bytes, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(reconstructed_bytes, b"")

    # =========================================================
    # 2. REPLICATION, FAILOVER, AND SELF-HEALING
    # =========================================================
    def test_primary_node_failure_failover_download(self):
        content = b"Data with primary failure and replica failover."
        meta = file_manager.upload_file("failover_test.bin", content, block_size_mb=1)
        block = metadata_store.blocks[meta["block_ids"][0]]
        primary_node_id = block["primary_node_id"]
        replica_node_id = block["replica_node_id"]

        # Take primary node OFFLINE
        node_manager.set_node_status(primary_node_id, "OFFLINE")

        # Download should succeed by failing over to replica
        reconstructed_bytes, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(reconstructed_bytes, content)

    def test_corrupted_block_detection_and_self_healing(self):
        content = b"Integrity check for auto self-healing block mechanism."
        meta = file_manager.upload_file("integrity_test.bin", content, block_size_mb=1)
        block = metadata_store.blocks[meta["block_ids"][0]]
        primary_path = block["primary_file_path"]

        # Tamper with the primary block bytes on disk
        with open(primary_path, "wb") as f:
            f.write(b"CORRUPTED_GARBAGE_BYTES")

        # Download should detect corrupted primary, failover to replica, and self-heal primary
        reconstructed_bytes, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(reconstructed_bytes, content)

        # Verify that primary block was self-healed on disk
        with open(primary_path, "rb") as f:
            healed_bytes = f.read()
        self.assertEqual(healed_bytes, content)

    def test_all_nodes_offline_raises_error(self):
        content = b"Data when all nodes go down."
        meta = file_manager.upload_file("all_offline.txt", content, block_size_mb=1)

        # Mark all nodes OFFLINE
        for nid in metadata_store.nodes:
            node_manager.set_node_status(nid, "OFFLINE")

        with self.assertRaises(IOError):
            file_manager.download_and_reconstruct_file(meta["id"])

    def test_cluster_repair_restores_under_replicated_blocks(self):
        content = b"Test re-replication repair on cluster."
        meta = file_manager.upload_file("repair_test.txt", content, block_size_mb=1)
        block = metadata_store.blocks[meta["block_ids"][0]]

        # Delete replica file physically to simulate lost replica disk
        if os.path.exists(block["replica_file_path"]):
            os.remove(block["replica_file_path"])

        # Run cluster repair
        res = recovery_manager.repair_cluster()
        self.assertGreaterEqual(res["repaired_count"], 1)

        # Verify replica now exists again on a healthy online node
        updated_block = metadata_store.blocks[meta["block_ids"][0]]
        self.assertTrue(os.path.exists(updated_block["replica_file_path"]))

    # =========================================================
    # 3. CAPACITY EXHAUSTION & ROLLBACK
    # =========================================================
    def test_node_capacity_exhaustion_rollback(self):
        # Set all nodes capacity very small (0.01 MB = 10 KB)
        for nid in metadata_store.nodes:
            node_manager.update_node_capacity(nid, 0.01)

        # Attempt to upload 500 KB file
        large_bytes = os.urandom(500 * 1024)
        with self.assertRaises(IOError):
            file_manager.upload_file("huge.bin", large_bytes, block_size_mb=1)

        # Verify metadata store has no orphaned files or blocks
        self.assertEqual(len(metadata_store.files), 0)
        self.assertEqual(len(metadata_store.blocks), 0)

    # =========================================================
    # 4. DIRECTORY NAVIGATION, RENAME, AND RECURSIVE DELETE
    # =========================================================
    def test_folders_navigation_rename_and_deletion(self):
        folder = file_manager.create_folder("Projects", parent_id="root")
        self.assertEqual(folder["name"], "Projects")

        file_meta = file_manager.create_text_file("code.py", "print('hello')", folder_id=folder["id"])
        self.assertEqual(file_meta["folder_id"], folder["id"])

        # Rename file
        renamed = file_manager.rename_file(file_meta["id"], "main.py")
        self.assertEqual(renamed["name"], "main.py")

        # Browse directory
        contents = file_manager.list_folder_contents(folder["id"])
        self.assertEqual(len(contents["files"]), 1)
        self.assertEqual(contents["files"][0]["name"], "main.py")
        self.assertGreater(len(contents["breadcrumbs"]), 1)

        # Recursive delete folder
        deleted = file_manager.delete_folder(folder["id"])
        self.assertTrue(deleted)
        self.assertNotIn(file_meta["id"], metadata_store.files)
        self.assertNotIn(folder["id"], metadata_store.folders)

    # =========================================================
    # 5. OS PROCESS MANAGEMENT & PROCESS HISTORY
    # =========================================================
    def test_process_lifecycle_and_history(self):
        pm = simulator_state.process_manager
        pid = pm.generate_pid()
        proc = pm.create_process(pid, "Compressor", "Batch", arrival_time=0, burst_time=4, state="NEW")
        self.assertEqual(proc["state"], "NEW")

        pm.update_state(pid, "READY")
        pm.update_state(pid, "RUNNING")
        pm.update_state(pid, "TERMINATED")

        history = pm.get_history()
        actions = [h["action"] for h in history if h["pid"] == pid]
        self.assertIn("CREATED", actions)
        self.assertIn("NEW -> READY", actions)
        self.assertIn("READY -> RUNNING", actions)
        self.assertIn("RUNNING -> TERMINATED", actions)

    # =========================================================
    # 6. CPU SCHEDULING ALGORITHMS
    # =========================================================
    def test_cpu_schedulers(self):
        procs = [
            {"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 2},
            {"pid": "P2", "arrival_time": 1, "burst_time": 3, "priority": 1},
            {"pid": "P3", "arrival_time": 2, "burst_time": 8, "priority": 3}
        ]

        # FCFS
        fcfs_res = fcfs_schedule(procs)
        self.assertEqual(fcfs_res["execution_order"], ["P1", "P2", "P3"])
        self.assertGreater(fcfs_res["averages"]["avg_waiting_time"], 0)

        # Round Robin
        rr_res = round_robin_schedule(procs, quantum=2)
        self.assertIn("P1", rr_res["execution_order"])
        self.assertGreaterEqual(len(rr_res["gantt_chart"]), 3)

        # Priority (P2 has priority 1 = highest)
        prio_res = priority_schedule(procs)
        self.assertIn("P1", prio_res["execution_order"])

        # SJF (Shortest Job First)
        sjf_res = sjf_schedule(procs)
        self.assertEqual(sjf_res["gantt_chart"][0]["pid"], "P1")

    # =========================================================
    # 7. MEMORY MANAGEMENT (FIRST, BEST, WORST FIT & COALESCING)
    # =========================================================
    def test_memory_allocation_and_coalescing(self):
        mm = MemoryManager(total_size=500)
        
        # Allocate blocks
        r1 = mm.allocate("P1", 100, "First Fit")
        self.assertTrue(r1["success"])
        r2 = mm.allocate("P2", 200, "Best Fit")
        self.assertTrue(r2["success"])

        metrics = mm.get_metrics()
        self.assertEqual(metrics["used_memory"], 300)
        self.assertEqual(metrics["free_memory"], 200)

        # Deallocate and verify coalescing
        mm.deallocate("P1")
        mm.deallocate("P2")
        metrics_after = mm.get_metrics()
        self.assertEqual(metrics_after["used_memory"], 0)
        self.assertEqual(metrics_after["free_memory"], 500)
        self.assertEqual(metrics_after["num_blocks"], 1)

    # =========================================================
    # 8. DISK SCHEDULING (FCFS, SSTF, SCAN)
    # =========================================================
    def test_disk_schedulers(self):
        head = 50
        reqs = [10, 90, 35, 70, 20]

        fcfs = fcfs_disk(head, reqs)
        self.assertEqual(fcfs["scheduled_sequence"], [50, 10, 90, 35, 70, 20])

        sstf = sstf_disk(head, reqs)
        self.assertEqual(sstf["scheduled_sequence"][1], 35) # 35 is closest to 50

        scan = scan_disk(head, reqs, direction="right", disk_size=200)
        self.assertTrue(all(scan["scheduled_sequence"][i] <= scan["scheduled_sequence"][i+1] 
                            for i in range(len(scan["scheduled_sequence"])-1) 
                            if scan["scheduled_sequence"][i] < 199 and scan["scheduled_sequence"][i+1] > 50))

        compare = compare_all_disk(head, reqs, direction="right", disk_size=200)
        self.assertIn("best_algorithm", compare)

    # =========================================================
    # 9. DEADLOCK BANKER'S ALGORITHM
    # =========================================================
    def test_deadlock_banker_algorithm(self):
        dm = DeadlockManager()
        safe_res = dm.check_safe_state()
        self.assertTrue(safe_res["is_safe"])
        self.assertGreater(len(safe_res["safe_sequence"]), 0)

        # Resource request
        req_res = dm.request_resources("P1", [1, 0, 2])
        self.assertTrue(req_res["granted"])

    # =========================================================
    # 10. SYNCHRONIZATION MUTEX & SEMAPHORE
    # =========================================================
    def test_synchronization_mutex_and_semaphore(self):
        # Mutex
        mutex = MutexSimulator("Test Mutex")
        res1 = mutex.acquire("P101")
        self.assertEqual(res1["status"], "ACQUIRED")
        res2 = mutex.acquire("P102")
        self.assertEqual(res2["status"], "WAITING")

        rel = mutex.release("P101")
        self.assertEqual(rel["status"], "RELEASED")
        self.assertEqual(mutex.owner_pid, "P102") # Granted to next waiting

        # Semaphore
        sem = SemaphoreSimulator("Printer", max_permits=2)
        self.assertEqual(sem.wait("P1")["status"], "GRANTED")
        self.assertEqual(sem.wait("P2")["status"], "GRANTED")
        self.assertEqual(sem.wait("P3")["status"], "BLOCKED")
        self.assertEqual(sem.signal()["status"], "RELEASED")
        self.assertIn("P3", sem.active_processes)

    # =========================================================
    # 11. FLASK API INTEGRATION ENDPOINTS
    # =========================================================
    def test_flask_api_endpoints(self):
        # Dashboard Summary
        dash = self.client.get("/api/dashboard/summary").get_json()
        self.assertTrue(dash["success"])
        self.assertIn("dfs", dash)

        # Upload file via HTTP POST
        data = {
            "file": (io.BytesIO(b"Flask HTTP upload test bytes"), "http_test.txt"),
            "block_size_mb": "1"
        }
        res_upload = self.client.post("/api/dfs/upload", data=data, content_type="multipart/form-data")
        json_up = res_upload.get_json()
        self.assertTrue(json_up["success"])
        file_id = json_up["file"]["id"]

        # Download file via HTTP GET
        res_down = self.client.get(f"/api/dfs/download/{file_id}")
        self.assertEqual(res_down.status_code, 200)
        self.assertEqual(res_down.data, b"Flask HTTP upload test bytes")

        # Rename file
        res_ren = self.client.post("/api/dfs/rename", json={"file_id": file_id, "new_name": "renamed_http.txt"})
        self.assertTrue(res_ren.get_json()["success"])

        # Delete file via HTTP DELETE
        res_del = self.client.delete(f"/api/dfs/file/{file_id}")
        self.assertTrue(res_del.get_json()["success"])

    # =========================================================
    # 12. NODE ALLOCATION ALGORITHMS (ROUND ROBIN, LOAD-BASED, FCFS)
    # =========================================================
    def test_node_allocation_algorithms_control_placement(self):
        # 1. Round Robin: sequential rotation across eligible nodes
        node_manager.set_allocation_algorithm("ROUND_ROBIN")
        content_rr = os.urandom(4 * 1024 * 1024) # 4 MB = 4 blocks of 1 MB
        meta_rr = file_manager.upload_file("rr_file.bin", content_rr, block_size_mb=1)
        
        # Verify primary blocks rotate across nodes
        rr_primary_nodes = [metadata_store.blocks[b_id]["primary_node_id"] for b_id in meta_rr["block_ids"]]
        self.assertEqual(len(set(rr_primary_nodes)), len(metadata_store.nodes))
        # Verify replicas are on different nodes
        for b_id in meta_rr["block_ids"]:
            b = metadata_store.blocks[b_id]
            self.assertNotEqual(b["primary_node_id"], b["replica_node_id"])

        # 2. Load-Based: selects node with highest free capacity
        # Make node3 have significantly more free space
        metadata_store.nodes["node1"]["free_mb"] = 50.0
        metadata_store.nodes["node2"]["free_mb"] = 30.0
        metadata_store.nodes["node3"]["free_mb"] = 400.0
        metadata_store.nodes["node4"]["free_mb"] = 20.0
        node_manager.set_allocation_algorithm("LOAD_BASED")

        content_lb = os.urandom(1024 * 1024) # 1 MB
        meta_lb = file_manager.upload_file("lb_file.bin", content_lb, block_size_mb=1)
        lb_primary_node = metadata_store.blocks[meta_lb["block_ids"][0]]["primary_node_id"]
        self.assertEqual(lb_primary_node, "node3") # Picked highest free space

        # 3. FCFS: fills first eligible node in order
        metadata_store.reset()
        node_manager.set_allocation_algorithm("FCFS")
        content_fcfs = os.urandom(2 * 1024 * 1024)
        meta_fcfs = file_manager.upload_file("fcfs_file.bin", content_fcfs, block_size_mb=1)
        fcfs_primary_nodes = [metadata_store.blocks[b_id]["primary_node_id"] for b_id in meta_fcfs["block_ids"]]
        self.assertEqual(fcfs_primary_nodes[0], "node1")
        self.assertEqual(fcfs_primary_nodes[1], "node1")

    # =========================================================
    # 13. SHARED DISK SCHEDULER & REAL I/O EXECUTION
    # =========================================================
    def test_shared_disk_scheduler_live_io_queue_and_algorithms(self):
        from backend.os_simulator.disk_scheduler import shared_disk_scheduler
        shared_disk_scheduler.clear_metrics()

        # Set scheduling algorithm to SSTF
        shared_disk_scheduler.set_algorithm("SSTF")
        self.assertEqual(shared_disk_scheduler.active_algorithm, "SSTF")

        # Perform file upload: real block writes must route through shared_disk_scheduler
        content = os.urandom(2 * 1024 * 1024) # 2 blocks of 1 MB
        meta = file_manager.upload_file("disk_sched_test.bin", content, block_size_mb=1)

        metrics = shared_disk_scheduler.get_queue_and_metrics()
        # 2 primary writes + 2 replica writes = at least 4 I/O operations
        self.assertGreaterEqual(metrics["total_requests_serviced"], 4)
        self.assertGreater(metrics["total_seek_cylinders"], 0)
        self.assertGreater(len(metrics["recent_history"]), 0)

        # Verify history events have real physical latency and simulated cylinders
        latest_event = metrics["recent_history"][0]
        self.assertIn("simulated_metrics", latest_event)
        self.assertIn("physical_operation", latest_event)
        self.assertEqual(latest_event["physical_operation"]["status"], "SUCCESS")
        self.assertGreaterEqual(latest_event["physical_operation"]["host_latency_ms"], 0)

        # Test API endpoints for disk algorithm and live metrics
        res_algo = self.client.post("/api/disk/algorithm", json={"algorithm": "SCAN", "direction": "left"}).get_json()
        self.assertTrue(res_algo["success"])
        self.assertEqual(shared_disk_scheduler.active_algorithm, "SCAN")
        self.assertEqual(shared_disk_scheduler.direction, "left")

        res_live = self.client.get("/api/disk/live_metrics").get_json()
        self.assertTrue(res_live["success"])
        self.assertEqual(res_live["live"]["active_algorithm"], "SCAN")

    # =========================================================
    # 14. CONCURRENT OPERATIONS & PROCESS SYNCHRONIZATION
    # =========================================================
    def test_concurrent_uploads_and_downloads(self):
        import concurrent.futures
        num_files = 4
        file_data = {
            f"concurrent_{i}.bin": os.urandom((i + 1) * 200 * 1024)
            for i in range(num_files)
        }
        hashes = {fname: hashlib.md5(data).hexdigest() for fname, data in file_data.items()}
        uploaded_metas = {}

        def upload_worker(fname_and_bytes):
            fname, data = fname_and_bytes
            return file_manager.upload_file(fname, data, block_size_mb=1)

        # Run concurrent uploads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_files) as executor:
            futures = {executor.submit(upload_worker, item): item[0] for item in file_data.items()}
            for future in concurrent.futures.as_completed(futures):
                fname = futures[future]
                meta = future.result()
                uploaded_metas[fname] = meta

        self.assertEqual(len(uploaded_metas), num_files)

        # Run concurrent downloads and verify checksum integrity
        def download_worker(file_id):
            return file_manager.download_and_reconstruct_file(file_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_files) as executor:
            dl_futures = {
                executor.submit(download_worker, meta["id"]): fname
                for fname, meta in uploaded_metas.items()
            }
            for future in concurrent.futures.as_completed(dl_futures):
                fname = dl_futures[future]
                reconstructed_bytes, _ = future.result()
                self.assertEqual(hashlib.md5(reconstructed_bytes).hexdigest(), hashes[fname])

    # =========================================================
    # 15. END-TO-END WORKFLOW: UPLOAD -> STORAGE -> REPLICATION -> FAILURE -> REPAIR -> DOWNLOAD
    # =========================================================
    def test_end_to_end_upload_storage_replication_failure_repair_download(self):
        # 1. Upload multi-block file
        original_data = b"End-to-End Reliability Workflow Verification.\n" * 50000 # ~2.3 MB
        original_hash = hashlib.md5(original_data).hexdigest()

        meta = file_manager.upload_file("e2e_verified.dat", original_data, block_size_mb=1, algorithm="ROUND_ROBIN")
        self.assertGreater(meta["total_blocks"], 1)

        # 2. Check blocks on physical storage folders
        first_block = metadata_store.blocks[meta["block_ids"][0]]
        p_node_id = first_block["primary_node_id"]
        r_node_id = first_block["replica_node_id"]
        self.assertTrue(os.path.exists(first_block["primary_file_path"]))
        self.assertTrue(os.path.exists(first_block["replica_file_path"]))

        # 3. Simulate Primary Node Failure
        node_manager.set_node_status(p_node_id, "OFFLINE")

        # 4. Failover Download should succeed from surviving replica
        dl_bytes_failover, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(hashlib.md5(dl_bytes_failover).hexdigest(), original_hash)

        # 5. Trigger Cluster Repair to re-replicate under-replicated block to another healthy online node
        repair_res = recovery_manager.repair_cluster(algorithm="LOAD_BASED")
        self.assertGreaterEqual(repair_res["repaired_count"], 1)

        # 6. Verify full reconstruction after repair
        final_dl_bytes, _ = file_manager.download_and_reconstruct_file(meta["id"])
        self.assertEqual(hashlib.md5(final_dl_bytes).hexdigest(), original_hash)
        self.assertEqual(final_dl_bytes, original_data)

if __name__ == "__main__":
    unittest.main()
