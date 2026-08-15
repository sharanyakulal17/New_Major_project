import os
import time

filename = "disk_test_file.bin"

print("Disk Stress Test Started... - disk_stress.py:6")

try:
    while True:
        # Write 100 MB
        with open(filename, "wb") as f:
            f.write(os.urandom(100 * 1024 * 1024))

        # Read the same file
        with open(filename, "rb") as f:
            f.read()

        # Delete it
        os.remove(filename)

        print("100 MB Written → Read → Deleted - disk_stress.py:21")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nDisk Stress Test Stopped. - disk_stress.py:26")