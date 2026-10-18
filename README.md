# A-Unified-OS-and-DBMS-Distributed-Storage-Simulator-By-Sync_Squad
An interactive Distributed File System Simulator integrating OS and DBMS concepts. It supports file operations, block distribution across virtual nodes, FCFS and SSTF scheduling, mutex synchronization, Banker’s Algorithm, block replication, node-failure recovery, relational metadata tracking, and real-time activity monitoring.
# Coding Phase 
# Operating System Concepts Simulator (Phase 1)

An interactive, educational Operating System (OS) Simulator featuring a modern web-based UI dashboard. Built for college project demonstration and viva presentation.


# Quick Start & Installation

# Prerequisites
* Python 3.8+  (Tested on Python 3.11)
* Web Browser (Chrome, Firefox, Edge, Safari)

### Installation Commands

1. **Clone / Open the project directory**:
   ```bash
   cd c:\Users\HP\Downloads\dfs_project
   ```

2. **Install Dependencies** (Flask is the only requirement):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Simulator**:
   ```bash
   python run.py
   ```
   *Alternatively:*
   ```bash
   python backend/app.py
   ```

4. **Open in Browser**:
   Navigate to **`http://127.0.0.1:5000`** in your browser.

---

## 🏛️ System Architecture

The application is built with a decoupled, modular architecture:

```
dfs_project/
├── backend/
│   ├── app.py                     # Flask application factory
│   ├── routes/
│   │   ├── api_routes.py          # REST API endpoints for all OS modules
│   │   └── view_routes.py         # Web page template rendering routes
│   ├── os_simulator/              # Pure Python OS Algorithm Engine
│   │   ├── process_manager.py     # PCB creation & state transitions (NEW, READY, RUNNING, WAITING, TERMINATED)
│   │   ├── cpu_scheduler.py       # FCFS, Round Robin, Priority Scheduling, SJF
│   │   ├── memory_manager.py      # First Fit, Best Fit, Worst Fit contiguous RAM allocation
│   │   ├── disk_scheduler.py      # FCFS, SSTF, SCAN disk track scheduling
│   │   ├── deadlock_manager.py    # Banker's Algorithm avoidance & safe sequence calculation
│   │   └── synchronization.py   # Mutex & Semaphore critical section locks
│   ├── models/
│   │   └── simulator_state.py    # Centralized in-memory simulator state store
│   └── utils/
│       └── logger.py              # System activity log engine
├── frontend/
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html              # Sidebar navigation & layout wrapper
│   │   ├── index.html             # Main summary dashboard
│   │   ├── process.html           # Process management UI
│   │   ├── cpu.html               # CPU scheduling UI & Gantt chart
│   │   ├── memory.html            # Memory manager UI & memory map bar
│   │   ├── disk.html              # Disk scheduler UI & track movement graph
│   │   ├── deadlock.html          # Deadlock avoidance & Banker's matrix UI
│   │   ├── sync.html              # Mutex & Semaphore concurrency UI
│   │   └── logs.html              # Terminal activity log stream
│   └── static/
│       ├── css/style.css          # Custom dark modern dashboard stylesheet
│       └── js/                    # Modular JavaScript controllers
├── run.py                         # Main execution launcher
├── requirements.txt               # Dependency list
└── README.md                      # Documentation
```

---

## 📖 OS Concepts & Module Viva Explanation Guide

### 1. Process Management (`process_manager.py`)
- **Process Control Block (PCB)**: Stores `pid`, `name`, `type`, `arrival_time`, `burst_time`, `priority`, and `state`.
- **States**:
  - `NEW`: Process initialized.
  - `READY`: Waiting in Ready Queue to be assigned CPU time.
  - `RUNNING`: Currently executing on the CPU core.
  - `WAITING`: Blocked waiting for I/O operation completion.
  - `TERMINATED`: Finished execution.

### 2. CPU Scheduling (`cpu_scheduler.py`)
- **FCFS**: First-Come, First-Served non-preemptive queue.
- **Round Robin (RR)**: Time-sliced scheduling using configurable **Time Quantum ($Q$)**.
- **Priority Scheduling**: Selects process with highest priority (lowest priority number).
- **SJF**: Shortest Job First non-preemptive selection.
- **Calculated Metrics**:
  - **Completion Time ($CT$)**: Time at which process finishes execution.
  - **Turnaround Time ($TAT = CT - AT$)**: Total time from arrival to completion.
  - **Waiting Time ($WT = TAT - BT$)**: Total time spent in ready queue.
  - **Response Time ($RT$)**: Time from arrival until first CPU execution block.

### 3. Memory Management (`memory_manager.py`)
- **Simulated RAM**: 1000 MB fixed capacity.
- **Dynamic Allocation Strategies**:
  - **First Fit**: Allocates the first free memory partition large enough to satisfy request.
  - **Best Fit**: Allocates the smallest suitable free partition to minimize wasted space.
  - **Worst Fit**: Allocates the largest available free partition.
- **Coalescing**: Automatically merges adjacent free partitions when memory is released.

### 4. Disk Scheduling (`disk_scheduler.py`)
- **FCFS**: Services disk track requests in order of arrival.
- **SSTF (Shortest Seek Time First)**: Selects request closest to current head position.
- **SCAN (Elevator Algorithm)**: Moves towards disk boundary (0 or 199), servicing requests along the way before reversing.

### 5. Deadlock Avoidance (`deadlock_manager.py`)
- **Banker's Algorithm**:
  - **Need Matrix**: $Need_{i,j} = Max_{i,j} - Allocation_{i,j}$
  - **Safety Check**: Iteratively checks if $Need_i \le Work$, updating $Work = Work + Allocation_i$.
  - **Safe Sequence**: Sequence of processes that completes execution without deadlock.

### 6. Process Synchronization (`synchronization.py`)
- **Mutex**: Binary lock (`UNLOCKED` / `LOCKED`) providing mutual exclusion to shared critical section.
- **Counting Semaphore**: Maintained permit count $S$. $P(S)$ decrements permits (blocks if $S=0$); $V(S)$ increments permits and unblocks waiting queue.

---

## 🔮 Integration with C++ Algorithms (Phase 2 Ready)

All algorithms in `backend/os_simulator/` are encapsulated in clean, isolated Python functions/classes. To replace any algorithm with high-performance C++ binaries in Phase 2:
1. Compile C++ algorithms into shared library binaries (`.dll` / `.so`) or pybind11 extensions.
2. Replace Python function calls in `backend/os_simulator/` with `ctypes` or C++ subprocess calls.
