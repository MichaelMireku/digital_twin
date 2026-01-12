#!/usr/bin/env python
"""
Combined runner for Railway deployment.
Starts the sensor simulator and processing service.
Note: API server runs separately on Render (see render.yaml).
"""
import subprocess
import sys
import os
import signal
import time

processes = []

def cleanup(signum=None, frame=None):
    """Terminate all child processes."""
    print("\nShutting down all services...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    print("Starting Depot Background Services (Railway)...")
    print("Note: API server runs on Render separately.")
    
    # Start sensor simulator (publishes to MQTT)
    sim_proc = subprocess.Popen(
        [sys.executable, "-m", "sensor_simulator.sensor_simulator"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(sim_proc)
    print(f"Sensor simulator started (PID: {sim_proc.pid})")
    
    # Give simulator a moment to start publishing
    time.sleep(2)
    
    # Start processing service (subscribes to MQTT and saves to DB)
    proc_proc = subprocess.Popen(
        [sys.executable, "processing_service.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(proc_proc)
    print(f"Processing service started (PID: {proc_proc.pid})")
    
    # Wait for processes
    while True:
        for proc in processes:
            if proc.poll() is not None:
                print(f"Process {proc.pid} exited with code {proc.returncode}")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
