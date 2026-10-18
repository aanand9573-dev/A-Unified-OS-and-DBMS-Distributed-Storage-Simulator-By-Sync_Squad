"""
CPU Scheduler Module
Implements CPU scheduling algorithms:
1. FCFS (First Come First Served)
2. Round Robin (RR with configurable Time Quantum)
3. Priority Scheduling (Non-preemptive & Preemptive)
4. SJF (Shortest Job First)

Calculates Gantt chart data, per-process metrics (CT, TAT, WT, RT), and averages.
"""

from backend.utils.logger import logger

def fcfs_schedule(processes):
    """
    First-Come, First-Served CPU Scheduling.
    processes: list of dicts [{'pid': 'P1', 'arrival_time': 0, 'burst_time': 5, 'priority': 1}, ...]
    """
    # Sort processes primarily by arrival time
    procs = sorted([dict(p) for p in processes], key=lambda x: (x['arrival_time'], x['pid']))
    
    current_time = 0
    gantt_chart = []
    metrics = {}
    
    for p in procs:
        pid = p['pid']
        at = p['arrival_time']
        bt = p['burst_time']
        
        # If CPU is idle until process arrives
        if current_time < at:
            gantt_chart.append({
                "pid": "IDLE",
                "start_time": current_time,
                "end_time": at,
                "duration": at - current_time
            })
            current_time = at
            
        start_time = current_time
        completion_time = start_time + bt
        current_time = completion_time
        
        turnaround_time = completion_time - at
        waiting_time = turnaround_time - bt
        response_time = start_time - at
        
        gantt_chart.append({
            "pid": pid,
            "start_time": start_time,
            "end_time": completion_time,
            "duration": bt
        })
        
        metrics[pid] = {
            "pid": pid,
            "arrival_time": at,
            "burst_time": bt,
            "priority": p.get('priority', 1),
            "start_time": start_time,
            "completion_time": completion_time,
            "turnaround_time": turnaround_time,
            "waiting_time": waiting_time,
            "response_time": response_time
        }
        
    return _compile_result("FCFS", gantt_chart, metrics)


def round_robin_schedule(processes, quantum=2):
    """
    Round Robin CPU Scheduling with specified time quantum.
    """
    quantum = max(1, int(quantum))
    procs = [dict(p) for p in processes]
    n = len(procs)
    if n == 0:
        return _compile_result("Round Robin", [], {})

    # Sort by arrival time initially
    procs.sort(key=lambda x: (x['arrival_time'], x['pid']))
    
    remaining_bt = {p['pid']: p['burst_time'] for p in procs}
    arrival_times = {p['pid']: p['arrival_time'] for p in procs}
    burst_times = {p['pid']: p['burst_time'] for p in procs}
    priorities = {p['pid']: p.get('priority', 1) for p in procs}
    first_exec = {}
    completion_times = {}
    
    current_time = 0
    gantt_chart = []
    ready_queue = []
    visited = set()
    
    # Function to add arrived processes to ready queue
    def check_new_arrivals(t):
        for p in procs:
            pid = p['pid']
            if p['arrival_time'] <= t and pid not in visited:
                ready_queue.append(pid)
                visited.add(pid)
                
    # Add processes at time 0
    check_new_arrivals(current_time)
    
    while ready_queue or any(remaining_bt[pid] > 0 for pid in remaining_bt):
        if not ready_queue:
            # CPU idle until next arrival
            unvisited = [p for p in procs if p['pid'] not in visited]
            if not unvisited:
                break
            next_at = min(p['arrival_time'] for p in unvisited)
            gantt_chart.append({
                "pid": "IDLE",
                "start_time": current_time,
                "end_time": next_at,
                "duration": next_at - current_time
            })
            current_time = next_at
            check_new_arrivals(current_time)
            continue
            
        pid = ready_queue.pop(0)
        
        if pid not in first_exec:
            first_exec[pid] = current_time
            
        exec_time = min(quantum, remaining_bt[pid])
        start_time = current_time
        end_time = current_time + exec_time
        current_time = end_time
        remaining_bt[pid] -= exec_time
        
        gantt_chart.append({
            "pid": pid,
            "start_time": start_time,
            "end_time": end_time,
            "duration": exec_time
        })
        
        # Check new arrivals during execution
        check_new_arrivals(current_time)
        
        if remaining_bt[pid] > 0:
            ready_queue.append(pid)
        else:
            completion_times[pid] = current_time
            
    metrics = {}
    for pid in burst_times:
        at = arrival_times[pid]
        bt = burst_times[pid]
        ct = completion_times.get(pid, 0)
        tat = ct - at
        wt = tat - bt
        rt = first_exec.get(pid, 0) - at
        metrics[pid] = {
            "pid": pid,
            "arrival_time": at,
            "burst_time": bt,
            "priority": priorities[pid],
            "start_time": first_exec.get(pid, 0),
            "completion_time": ct,
            "turnaround_time": tat,
            "waiting_time": wt,
            "response_time": rt
        }
        
    return _compile_result(f"Round Robin (Q={quantum})", gantt_chart, metrics)


def priority_schedule(processes):
    """
    Non-preemptive Priority Scheduling (Lower priority number = Higher priority).
    """
    procs = [dict(p) for p in processes]
    n = len(procs)
    if n == 0:
        return _compile_result("Priority Scheduling", [], {})

    completed = set()
    current_time = 0
    gantt_chart = []
    metrics = {}
    
    while len(completed) < n:
        available = [p for p in procs if p['arrival_time'] <= current_time and p['pid'] not in completed]
        
        if not available:
            uncompleted = [p for p in procs if p['pid'] not in completed]
            next_at = min(p['arrival_time'] for p in uncompleted)
            gantt_chart.append({
                "pid": "IDLE",
                "start_time": current_time,
                "end_time": next_at,
                "duration": next_at - current_time
            })
            current_time = next_at
            continue
            
        # Select highest priority (lowest priority number)
        best_p = min(available, key=lambda x: (x.get('priority', 1), x['arrival_time'], x['pid']))
        pid = best_p['pid']
        at = best_p['arrival_time']
        bt = best_p['burst_time']
        prio = best_p.get('priority', 1)
        
        start_time = current_time
        completion_time = start_time + bt
        current_time = completion_time
        
        turnaround_time = completion_time - at
        waiting_time = turnaround_time - bt
        response_time = start_time - at
        
        gantt_chart.append({
            "pid": pid,
            "start_time": start_time,
            "end_time": completion_time,
            "duration": bt
        })
        
        metrics[pid] = {
            "pid": pid,
            "arrival_time": at,
            "burst_time": bt,
            "priority": prio,
            "start_time": start_time,
            "completion_time": completion_time,
            "turnaround_time": turnaround_time,
            "waiting_time": waiting_time,
            "response_time": response_time
        }
        completed.add(pid)
        
    return _compile_result("Priority Scheduling", gantt_chart, metrics)


def sjf_schedule(processes):
    """
    Non-preemptive Shortest Job First (SJF).
    """
    procs = [dict(p) for p in processes]
    n = len(procs)
    if n == 0:
        return _compile_result("SJF", [], {})

    completed = set()
    current_time = 0
    gantt_chart = []
    metrics = {}
    
    while len(completed) < n:
        available = [p for p in procs if p['arrival_time'] <= current_time and p['pid'] not in completed]
        
        if not available:
            uncompleted = [p for p in procs if p['pid'] not in completed]
            next_at = min(p['arrival_time'] for p in uncompleted)
            gantt_chart.append({
                "pid": "IDLE",
                "start_time": current_time,
                "end_time": next_at,
                "duration": next_at - current_time
            })
            current_time = next_at
            continue
            
        # Select smallest burst time
        best_p = min(available, key=lambda x: (x['burst_time'], x['arrival_time'], x['pid']))
        pid = best_p['pid']
        at = best_p['arrival_time']
        bt = best_p['burst_time']
        
        start_time = current_time
        completion_time = start_time + bt
        current_time = completion_time
        
        turnaround_time = completion_time - at
        waiting_time = turnaround_time - bt
        response_time = start_time - at
        
        gantt_chart.append({
            "pid": pid,
            "start_time": start_time,
            "end_time": completion_time,
            "duration": bt
        })
        
        metrics[pid] = {
            "pid": pid,
            "arrival_time": at,
            "burst_time": bt,
            "priority": best_p.get('priority', 1),
            "start_time": start_time,
            "completion_time": completion_time,
            "turnaround_time": turnaround_time,
            "waiting_time": waiting_time,
            "response_time": response_time
        }
        completed.add(pid)
        
    return _compile_result("SJF", gantt_chart, metrics)


def _compile_result(algo_name, gantt_chart, metrics):
    if not metrics:
        return {
            "algorithm": algo_name,
            "gantt_chart": [],
            "process_metrics": [],
            "execution_order": [],
            "averages": {"avg_waiting_time": 0, "avg_turnaround_time": 0, "avg_response_time": 0}
        }
        
    metrics_list = list(metrics.values())
    metrics_list.sort(key=lambda x: x['pid'])
    
    total_wt = sum(m['waiting_time'] for m in metrics_list)
    total_tat = sum(m['turnaround_time'] for m in metrics_list)
    total_rt = sum(m['response_time'] for m in metrics_list)
    count = len(metrics_list)
    
    execution_order = [g['pid'] for g in gantt_chart if g['pid'] != "IDLE"]
    
    res = {
        "algorithm": algo_name,
        "gantt_chart": gantt_chart,
        "process_metrics": metrics_list,
        "execution_order": execution_order,
        "averages": {
            "avg_waiting_time": round(total_wt / count, 2),
            "avg_turnaround_time": round(total_tat / count, 2),
            "avg_response_time": round(total_rt / count, 2)
        }
    }
    logger.log("CPU", "success", f"Executed {algo_name}. Avg WT: {res['averages']['avg_waiting_time']}s, Avg TAT: {res['averages']['avg_turnaround_time']}s")
    return res
