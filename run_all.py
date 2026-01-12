#!/usr/bin/env python
"""
Combined runner for Railway deployment.
Starts both the API server and sensor simulator in parallel.
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
    
    print("Starting Depot Services...")
    
    # Start API server
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "api.app"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(api_proc)
    print(f"API server started (PID: {api_proc.pid})")
    
    # Give API a moment to start
    time.sleep(2)
    
    # Start sensor simulator
    sim_proc = subprocess.Popen(
        [sys.executable, "-m", "sensor_simulator.sensor_simulator"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(sim_proc)
    print(f"Sensor simulator started (PID: {sim_proc.pid})")
    
    # Wait for processes
    while True:
        for proc in processes:
            if proc.poll() is not None:
                print(f"Process {proc.pid} exited with code {proc.returncode}")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
