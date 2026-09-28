import psutil                         #reads your computers CPU, RAM, Disk, Network and running processes
import pandas as pd                   #Used for handling data
import time                           #Makes the program wait (for example, 5 seconds) before collecting the next reading.
from datetime import datetime         #Gets the current date and time.
import csv                            #Creates and writes data into the CSV file.
import os                             #Checks whether the CSV file already exists.

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(CURRENT_DIR, "datasets", "system_metrics.csv")          #Store the dataset in the datasets folder with the filename system_metrics.csv

if not os.path.exists(csv_file):
    with open(csv_file, mode="w", newline="")as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp",
            "CPU Usage (%)",
            "Memory Usage (%)",
            "Disk Usage (%)",
            "Disk Read",
            "Disk Write",
            "Bytes Sent",
            "Bytes Received",
            "Packets Sent",
            "Packets Received",
            "Running Processes",
            "System Uptime",
            "Service Status",
            "Response Time (ms)",
            "Health Check",
            "Status"
        ])

while True:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")            #current date and time(eg: 2026-07-13 18:45:20)
    cpu_usage = psutil.cpu_percent(interval = 1)                         #CPU Usage(eg: CPU = 18%)
    memory_usage = psutil.virtual_memory().percent                       #memory usage(eg: RAM = 42%)
    disk_usage = psutil.disk_usage('/').percent                          #disk usage(eg: Disk = 55%)
    disk_io = psutil.disk_io_counters()
    disk_read = disk_io.read_bytes                                       #Total bytes read from disk
    disk_write = disk_io.write_bytes                                     #Total bytes written to disk
    net_io = psutil.net_io_counters()                                   #network usage
    bytes_sent = net_io.bytes_sent                                      #eg: 12000
    bytes_received = net_io.bytes_recv                                  #eg: 15000
    
    # Network anomaly threshold
    if bytes_sent > 100000000 or bytes_received > 100000000:
        network_anomaly = True
    else:
        network_anomaly = False
    
    packets_sent = net_io.packets_sent                                   #Number of network packet sent
    packets_received = net_io.packets_recv                               #Number of network packet received

    running_processes = len(psutil.pids())                               #It counts how many programs/processes are currently running(eg:184)  

    #System Uptime (seconds)
    boot_time = psutil.boot_time()
    system_uptime = int(time.time() - boot_time)                         #How long the system has been running

    #Response Time (milliseconds)
    response_time = round(psutil.cpu_times_percent().idle, 2)            #A simple metric
    
    #Health Check and Service Status
    if cpu_usage > 90 or memory_usage > 90 or disk_usage > 95 or network_anomaly:
        health_check = "Unhealthy"
        service_status = "Degraded"
        status = "Anomaly"
    else:
        health_check = "Healthy"
        service_status = "Running"
        status = "Normal"

    #save the collected data into CSV file
    with open(csv_file, mode="a", newline="")as file:                   #It adds new rows to the end of the CSV file instead of deleting the old data
        writer = csv.writer(file)                                       #This creates an object that can write rows into the CSV file.
        writer.writerow([                                               #This writes one complete record into system_metrics.csv
            timestamp,
            cpu_usage,
            memory_usage,
            disk_usage,
            disk_read,
            disk_write,
            bytes_sent,
            bytes_received,
            packets_sent,
            packets_received,
            running_processes,
            system_uptime,
            service_status,
            response_time,
            health_check,
            status
        ])

    print(f"{timestamp}  Data Saved Successfully! - collect_metrics.py:94")

    #Wait for 5 seconds before collecting the next data
    time.sleep(5)                                                     #Pause the program for 5 seconds before collecting the next record