import time

memory_list = []

print("Memory Stress Test Started... - memory_stress.py:5")

try:
    while True:
        # Allocate about 10 MB every second
        memory_list.append(bytearray(200 * 1024 * 1024))
        print(f"Allocated {len(memory_list) * 200} MB - memory_stress.py:11")
        time.sleep(1)

except KeyboardInterrupt:
    print("\nMemory Stress Test Stopped. - memory_stress.py:15")