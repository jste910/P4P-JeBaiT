import smbus2
"""
The code in this file isn't necessarily used, but is being kept as
a legacy product incase these functions are needed in the future.

"""

def findDevices():
    bus = smbus2.SMBus(4) # Not sure if we will change 1
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