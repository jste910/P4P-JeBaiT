
#imports
import time
import smbus2
import subprocess
import threading
# defines
# Input output readings, these need to be confirmed
VOUT_LOCATION = 0
IOUT_LOCATION = 0
VIN_LOCATION = 0x16
IIN_LOCATION = 0x17 # Doesn't exist?
DEVICE_ADDRESS = 0x13  # Example device address, change as needed
BUS_ADDRESS = 0
BUS_NUMBER = 4
VCCINT_RAIL = 0x13
VCCBRAM_RAIL = 0x14
VOLTAGE_RAIL = VCCINT_RAIL
DESTINATION_REGISTER = 0x21
ZCU102_NOM = 0.85
NOMINAL_VOLTAGE = ZCU102_NOM
BUS_LINE = smbus2.SMBus(BUS_NUMBER)

# Power calcuulations
# Power = Voltage * Current

# efficiency = Power out / Power in

# PMBus is little ndian

# exit()
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

def read_data(bus, device_address, location):
    try:
        # Read the data from the device
        data = bus.read_word_data(device_address, location)
        return data
    except OSError as e:
        print(f"Error reading from device at address {hex(device_address)}: {e}")
        return None

def write_data(bus, device_address, location, data):
    try:
        bus.write_word_data(device_address, location, data)
        return True
    except OSError as e:
        print(f"Error writing to device at address {hex(device_address)}: {e}")
        return False

def test():
    # find the buses that are available
    device_list = findDevices()

    if not device_list:
        print("No devices found.")
        exit(1)


    # working buses? a, b. 10, 11, 13, 14, 15, 16, 17, 18, 1a, 1b, 1d

    # we have at least one device
    print(f"Found {len(device_list)} devices.")
    for device in device_list:
        print(f"Device address: {hex(device)}")
    exit()

bus = smbus2.SMBus(4)

def setVoltage(bus, address, destination, voltageDecimal):
    """
    :param bus: The bus that the sensor is connected to
    :param address: The address of the rail that we want to read
    :param destination: The actual value inside the rail (See datasheet)
    :param voltageDecimal: The voltage to be written to the rail AS A DECIMAL
    :return: None
    """

    # voltageDecimal # This needs to be converted to a value between 0 and 4096 and written into hex
    if voltageDecimal < 0 or voltageDecimal > 1: # out of bounds
        raise Exception(f"Voltage must be between 0 and 1, entered voltage: {voltageDecimal}")

    try:
        bus.write_word_data(address, destination, (int(voltageDecimal*4096)))
        return True
    except OSError as e:
        print(f"Error writing to device at address {hex(address)}: {e}")
        return False

# setVoltage(smbus2.SMBus(4), 0x13, 0x21, 0.85)  # reset back to normal

# print("Logging data...")
# count = 1 # only run the script for ~ 10s
# while count > 0:
#     def rloop(bus, location):
#         alt = read_data(bus, 0x13, location)
#         if alt is not None:
#             print(f"{location}: {hex(alt)} || {alt}")

#     # attempting to write

#     # write_data(bus, 0x13, 0x21, 0x0800) # down by literally nothing


#     # write_data(bus, 0x13, 0x21, 0xd99) # just a little under nominal
#     print("Done")
#     for i in range(20):
#         time.sleep(0.25)
#         # balt = read_data(bus, 0x13, 0x21)
#         rloop(bus, 0x21)
#         # if balt is not None:
#         #     print(f"{hex(balt)}")
#     time.sleep(0.25) # wait for 1 second before the next reading
#     count-=1
# setVoltage(smbus2.SMBus(4), 0x13, 0x21, 0.85)  # reset back to normal
# cwd = "."
# cmd = "./bin/CapsuleNetwork.exe model/partial_caps.xmodel xclbin/four_kernels.xclbin img/MNIST/t10k-images-idx3-ubyte weights/new_digitcaps_weights.txt 100 img/MNIST/t10k-labels-idx1-ubyte"
# subprocess.run(cmd, shell=True, cwd=cwd)

# define the stop event
stop_event = threading.Event()

def stop():
    stop_event.set()

def runCommand(cmd, cwd):
    subprocess.run(cmd, shell=True, cwd=cwd)

def readData(bus, device_address, location):
    try:
        # Read the data from the device
        data = bus.read_word_data(device_address, location)
        return data
    except OSError as e:
        print(f"Error reading from device at address {hex(device_address)}: {e}")
        return None

def readAll(bus, voltageLocation, currentLocation):
    alt = readData(bus, VOLTAGE_RAIL, voltageLocation)
    alt2 = readData(bus, VOLTAGE_RAIL, currentLocation)
    if alt is not None and alt2 is not None:
        print(f"Power: {alt/4096:.2f}V x {alt2/4096:.2f}A = {(alt/4096)*(alt2/4096):.2f}W")
        # print(f"Power: {alt/4096:.2f}V ({alt}) x {alt2/4096:.2f}A ({alt2})= {(alt/4096)*(alt2/4096):.2f}W") # debug

def getReadingsBus(busNumber, safe = True):
    # safe = True means that we are threading and safe = False means we are not
    bus = smbus2.SMBus(busNumber)
    if not safe:
        readAll(bus, 0x8B, 0x8C)
        return # we want to get out of here
    try:
        while not stop_event.is_set() and safe:
            readAll(bus, 0x8B, 0x8C)
            time.sleep(0.25)
    except KeyboardInterrupt:
        stop_event.set()

def undervoltingLoop(initialvoltage, cwd, cmd, iter, step):
    volt = initialvoltage
    for _ in range(iter):
        print("==============================")
        print(f"Voltage: {volt:.2f}")
        print("==============================")
        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, volt)
        runCommand(cmd, cwd)
        volt -= step
    setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal
    stop()

def cmdBuilder(exepath, modelpath, xclpath, imgpath, weightspath, images, labelspath):
    return f"{exepath} {modelpath} {xclpath} {imgpath} {weightspath} {images} {labelspath}"

def main():

    # All constants
    cwd = "."
    HOME_PATH = "/run/media/mmcblk0p1"

    EXE_PATH = f"{HOME_PATH}/capsnet/bin/CapsuleNetwork.exe"
    MODEL_PATH = f"{HOME_PATH}/capsnet/model/partial_caps.xmodel"
    XCL_PATH = f"{HOME_PATH}/four_kernels_150MHz.xclbin"
    IMG_PATH = f"{HOME_PATH}/capsnet/img/MNIST/t10k-images-idx3-ubyte"
    WEIGHTS_PATH = f"{HOME_PATH}/capsnet/weights/new_digitcaps_weights.txt"
    IMAGES = "1"
    LABELS_PATH = f"{HOME_PATH}/capsnet/img/MNIST/t10k-labels-idx1-ubyte"

    # The nomial voltage is 0.85
    ITER = 28
    STEP = 0.01

    isThreaded = True
    setVoltage(smbus2.SMBus(BUS_NUMBER), VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)

    print("=======================")
    print("=== Model Selection ===")
    print("1. 1 Image")
    print("2. 10 Images")
    print("3. 25 Image")
    print("4. 100 Image")
    print("5. 1000 Image")
    print("6. Custom Model")
    print("=======================")
    modelchoice = input(f"Please select a number of images (default is 10): ")
    if modelchoice.isnumeric(): # if it is numeric
        mchoice = int(modelchoice)
        if mchoice == 1:
            IMAGES = "1"
        elif mchoice == 2:
            IMAGES = "10"
        elif mchoice == 3:
            IMAGES = "25"
        elif mchoice == 4:
            IMAGES = "100"
        elif mchoice == 5:
            IMAGES = "1000"
        elif mchoice == 6:
            IMAGES = input("Please enter the number of images: ")
            if not IMAGES.isnumeric():
                raise Exception(f"{IMAGES} is not a valid number of images")
            ITER = int(input("Please enter the number of iterations (type: integer): "))
            STEP = float(input("Please enter the step size (type: float): "))
            print("==============================")
            print("====== Running Command =======")
            print("==============================")

        else:
            raise Exception(f"{mchoice} is an invalid choice")
    else: # if it is not numeric (either blank or other input)
        print(f"Using 10 images as default")
        IMAGES = "10"

    print("==============================")
    print(f"========= Hi Maryam =========")
    print("==============================")

    if ITER > 28:
        print(f"Warning: ITER is set to {ITER}, which is greater than 28. This may cause the voltage to drop below 0.57V, which is unsafe for the device.")
        print("Please ensure that you are aware of the risks before proceeding.")

    if NOMINAL_VOLTAGE - ITER*STEP < 0.57:
        print(f"Warning: The final voltage after {ITER} iterations will be {NOMINAL_VOLTAGE - ITER*STEP:.2f}V, which is below the safe limit of 0.57V.")
        print("Please ensure that you are aware of the risks before proceeding.")

    cmd = cmdBuilder(EXE_PATH, MODEL_PATH, XCL_PATH, IMG_PATH, WEIGHTS_PATH, IMAGES, LABELS_PATH)

    if isThreaded:
        monitorThread = threading.Thread(target=getReadingsBus, args=(4, True,), daemon=True)
        shellThread = threading.Thread(target=undervoltingLoop, args=(NOMINAL_VOLTAGE, cwd, cmd, ITER, STEP), daemon=True)
        print("Threads started")
        monitorThread.start()
        shellThread.start()
        try:
            while monitorThread.is_alive() or shellThread.is_alive():
                monitorThread.join(timeout=1)
                shellThread.join(timeout=1)

        except KeyboardInterrupt:
            print("Shutting down")
            # end all other processes
            setVoltage(smbus2.SMBus(4), VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)  # reset back to normal
            exit(1)
    else: # not threaded
        # not running anything
        pass

    setVoltage(smbus2.SMBus(4), VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)  # reset back to normal
    print("==============================")
    print("==========Finished============")
    print("==============================")

if __name__ == "__main__":
    main()
