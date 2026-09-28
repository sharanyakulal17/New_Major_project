"""
Unified System Stress Testing Suite
Provides controllable stress generation across CPU, Memory, Disk, and Network
to trigger and validate anomaly detection and self-healing pipelines.
"""

import os
import sys
import time
import socket
import argparse
import multiprocessing
from datetime import datetime

def cpu_worker(duration_sec, intensity=10000000):
    """Generates CPU load on a single core for a given duration."""
    start_time = time.time()
    x = 0
    while True:
        if duration_sec and (time.time() - start_time) > duration_sec:
            break
        for i in range(intensity):
            x += i * i

def stress_cpu(duration=10, cores=None):
    """Stress CPU across multiple or all available CPU cores."""
    total_cores = cores or multiprocessing.cpu_count()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting CPU stress on {total_cores} cores for {duration}s...")
    processes = []
    for _ in range(total_cores):
        p = multiprocessing.Process(target=cpu_worker, args=(duration,))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU stress completed.")

def stress_memory(duration=10, mb_per_sec=200, max_alloc_mb=2000):
    """Stress RAM by sequentially allocating memory blocks."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Memory stress (allocating {mb_per_sec}MB/s up to {max_alloc_mb}MB) for {duration}s...")
    memory_blocks = []
    start_time = time.time()
    try:
        while time.time() - start_time < duration:
            allocated = len(memory_blocks) * mb_per_sec
            if allocated < max_alloc_mb:
                memory_blocks.append(bytearray(mb_per_sec * 1024 * 1024))
                print(f"  -> Allocated: {len(memory_blocks) * mb_per_sec} MB RAM")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMemory stress interrupted by user.")
    finally:
        memory_blocks.clear()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Memory stress completed & memory freed.")

def stress_disk(duration=10, block_size_mb=100, target_dir="."):
    """Stress Disk by rapidly writing, reading, and flushing binary blocks."""
    test_file = os.path.join(target_dir, ".disk_stress_temp.bin")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Disk I/O stress ({block_size_mb}MB chunks) for {duration}s...")
    start_time = time.time()
    iterations = 0
    try:
        while time.time() - start_time < duration:
            # Write block
            with open(test_file, "wb") as f:
                f.write(os.urandom(block_size_mb * 1024 * 1024))
                f.flush()
                os.fsync(f.fileno())
            # Read block
            with open(test_file, "rb") as f:
                _ = f.read()
            # Remove block
            if os.path.exists(test_file):
                os.remove(test_file)
            iterations += 1
            print(f"  -> Disk cycle #{iterations}: {block_size_mb} MB written & read.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nDisk stress interrupted by user.")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Disk stress completed ({iterations} cycles).")

def stress_network(duration=10, packet_count=1000):
    """Stress Network by transmitting UDP bursts to localhost."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Network packet burst stress for {duration}s...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = os.urandom(1024)  # 1 KB payload
    start_time = time.time()
    sent = 0
    try:
        while time.time() - start_time < duration:
            for _ in range(packet_count):
                try:
                    sock.sendto(data, ("127.0.0.1", 9999))
                    sent += 1
                except Exception:
                    pass
            time.sleep(0.1)
    finally:
        sock.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Network stress completed ({sent} packets transmitted).")

def run_stress_suite(test_type="all", duration=10):
    """Runs a single or combined stress test suite."""
    print(f"==================================================")
    print(f"   SYSTEM STRESS TEST RUNNER: [{test_type.upper()}]")
    print(f"   Duration: {duration}s | Timestamp: {datetime.now()}")
    print(f"==================================================")
    
    if test_type == "cpu":
        stress_cpu(duration)
    elif test_type == "memory":
        stress_memory(duration)
    elif test_type == "disk":
        stress_disk(duration)
    elif test_type == "network":
        stress_network(duration)
    elif test_type == "all":
        print("\n--- Phase 1: CPU Stress ---")
        stress_cpu(duration=min(5, duration))
        print("\n--- Phase 2: Memory Stress ---")
        stress_memory(duration=min(5, duration))
        print("\n--- Phase 3: Disk Stress ---")
        stress_disk(duration=min(5, duration))
        print("\n--- Phase 4: Network Stress ---")
        stress_network(duration=min(5, duration))
        print("\nAll stress test phases finished successfully.")
    else:
        print(f"Unknown test type: {test_type}. Choose from: cpu, memory, disk, network, all")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="System Stress Test Suite for Self-Healing Validation")
    parser.add_argument("--type", choices=["cpu", "memory", "disk", "network", "all"], default="all", help="Target subsystem to stress")
    parser.add_argument("--duration", type=int, default=10, help="Test duration in seconds (default: 10)")
    parser.add_argument("--cores", type=int, default=None, help="Number of CPU cores to stress (default: all cores)")
    args = parser.parse_args()
    
    run_stress_suite(test_type=args.type, duration=args.duration)
