import os
import glob
import smbus2
import time
import threading
import subprocess
import argparse

def findDevices(busno = 4):
    bus = smbus2.SMBus(busno) # Not sure if we will change 1
    print("Scanning for devices")
    devices = []
    for address in range(0x03, 0x20):
        try:
            bus.write_quick(address) # Check if the device is present
            devices.append(address)
            print(f"Device found at address: {hex(address)}")
        except (OSError, IOError):
            # Device not found, continue scanning
            continue
    bus.close()
    print("Try again")
    for bus_num in range(0, 23):
        try:
            bus = smbus2.SMBus(bus_num)
            bus.write_quick(0x1A)
            print(f"Found device at 0x1A on bus {bus_num}")
        except:
            continue

    return devices

def test():
    # find the buses that are available
    for i in range(10):
        print(f" ================= Bus {i} ================ ")
        device_list = findDevices(i)

        if not device_list:
            print("No devices found.")
            exit(1)


        # working buses? a, b. 10, 11, 13, 14, 15, 16, 17, 18, 1a, 1b, 1d

        # we have at least one device
        print(f"Found {len(device_list)} devices.")
        for device in device_list:
            print(f"Device address: {hex(device)}")
    exit()

def main():
    test()

if __name__ == "__main__":
    main()
