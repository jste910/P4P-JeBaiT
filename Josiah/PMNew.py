
#imports
import glob
import os
import time
import smbus2
import subprocess
import threading
from datetime import datetime
import pexpect
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

RAILS = [{
    "name": "VCCINT",
    "address": 0x13,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"

},
{
    "name": "VCCBRAM",
    "address": 0x14,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"

}, {
    "name": "VCCAUX",
    "address": 0x15,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
}, {
    "name": "VCC1V2",
    "address": 0x16,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"

}, {
    "name": "VCC3V3",
    "address": 0x17,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"

}, {
    "name": "VCCDJ_FMC",
    "address": 0x18,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
},
{
    "name": "VCCPSINTFP",
    "address": 0x0A,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
}, {
    "name": "VCCPSINTLP",
    "address": 0x0B,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
    
}, {
    "name": "DDR4_DIMM_VDDQ",
    "address": 0x1D,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
}, {
    "name": "VCCOPS",
    "address": 0x10,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
}, {
    "name": "UTIL3V3",
    "address": 0x1A,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"

}, {
    "name": "UTIL5V0",
    "address": 0x1B,
    "vout_exponent": -12,
    "tags": "MAXIM_PMBUS"
},
]

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

def sign_extend(value, bits):
    """Sign-extend an integer encoded using the specified number of bits."""
    sign_bit = 1 << (bits - 1)
    return (value ^ sign_bit) - sign_bit

def decodeVoltage(raw_value, exponent = -12):
    return raw_value * (2.0 ** exponent)

def decodeCurrent(raw_word):
    """
    Decode a PMBus LINEAR11 value.

    Bits 15:11 contain a signed 5-bit exponent.
    Bits 10:0 contain a signed 11-bit mantissa.

    value = mantissa * 2**exponent
    """
    exponent = sign_extend((raw_word >> 11) & 0x1F, 5)
    mantissa = sign_extend(raw_word & 0x07FF, 11)
    return mantissa * (2.0 ** exponent)

lookup = {
        "ina226_u15" : "VCCOPS3",
        "ina226_u92" : "VCCPSDDRPLL",
        "ina226_u79" : "VCCINT",
        "ina226_u81" : "VCCBRAM",
        "ina226_u80" : "VCCAUX",
        "ina226_u84" : "VCC1V2",
        "ina226_u16" : "VCC3V3",
        "ina226_u65" : "CADJ_FMC",
        "ina226_u74" : "MGTAVCC",
        "ina226_u75" : "MGTAVTT",
        "ina226_u76" : "VCCPSINTFP",
        "ina226_u77" : "VCCPSINTLP",
        "ina226_u78" : "VCCPSAUX",
        "ina226_u87" : "VCCPSPLL",
        "ina226_u85" : "MGTRAVCC",
        "ina226_u86" : "MGTRAVTT",
        "ina226_u93" : "VCCO_PSDDR_504",
        "ina226_u88" : "VCCOPS",
        "max20751" : "VCC or VTT"
    }

def read_file(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except:
        return None

def print_sensor_values(hwmon):
    name = read_file(os.path.join(hwmon, "name"))
    if not name:
        print(f"Skipping {hwmon} ({name}) - not an INA226 device")
        return  # Only INA226 devices

    print(f"\n=== {hwmon} ({name} : {lookup[name]}) ===")

    # Possible sensor types to read
    sensor_types = ["in", "curr", "power"]
    rst = ""
    for sensor_type in sensor_types:
        files = glob.glob(os.path.join(hwmon, f"{sensor_type}*_input"))
        for file_path in files:
            base = os.path.basename(file_path).replace("_input", "")
            label_path = os.path.join(hwmon, f"{base}_label")
            label = read_file(label_path) or base
            value = read_file(file_path)
            if value:
                unit = {
                    "in": "mV",
                    "curr": "mA",
                    "power": "uW" # I think this is the more appropriate unit
                }.get(sensor_type, "")
                print(f"{label}: {int(value)} {unit}")
                rst += f"{int(value)},"
    return rst
# def getReadings(filePath, vccint, safe = True):
#     # safe = True means that we are threading and salfe = False means we are not
#     if not safe:
#         print_sensor_values(f"{filePath}{vccint}") # run until the stop event is set
#         return
#     while not stop_event.is_set() and safe:
#         print_sensor_values(f"{filePath}{vccint}") # run until the stop event is set
#         time.sleep(0.25) # short break



def ping_host(host, count=1, timeout=2):
    try:
        # Ping command depends on platform; this works on Linux/macOS
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0 # success
    except Exception:
        return False

def offload(lst):

    ipAddress = "192.168.9.1"
    user = "beta"

    fileLocationLocal = f"/home/root/UV_outputs/digit_caps/{lst}"
    dest = "/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/"
    cmd = f"scp -r {fileLocationLocal} {user}@{ipAddress}:{dest}"
    print(cmd)
    if not ping_host(ipAddress):
        print(f"Ping failed at: {ipAddress}")
        # setup the connection
        return # reject

    print("All checks passed")

    try:
        print(f"Executing command: {cmd}")

        child = pexpect.spawn(cmd)
        child.expect('password:')
        child.sendline(' ')
        for line in child: # progress bar
            print(f"Line: {line.decode('utf-8').strip()}")

        print("Copied successfully")

        # remove the directory after copying
        if os.path.isdir(fileLocationLocal):
            print(f"Removing directory: {fileLocationLocal}")
            subprocess.run(f"rm -rf {fileLocationLocal}", shell=True)
            print("Directory removed successfully")

    except Exception as e:
        print(f"Error: {e}")

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

def readAll(bus, voltageLocation, currentLocation, file=False):
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Timestamp: {datetime_now}")
    line = datetime_now + ","
    for i in range(20):
        line += print_sensor_values(f"{'/sys/class/hwmon/hwmon'}{i}") # run until the stop event is set
    for rail in RAILS:
        alt = readData(bus, rail["address"], voltageLocation)
        alt2 = readData(bus, rail["address"], currentLocation)
        if alt is not None and alt2 is not None:
            decodedalt = decodeVoltage(alt)
            decodedalt2 = decodeCurrent(alt2)
            # print(f"Rail: {rail['name']} | Power: {alt:.2f}V x {alt2:.2f}A = {((alt/4096)*(alt2/4096)):.2f}W")
            # print(f"Rail: {rail['name']} | Power: {alt/4096:.2f}V x {alt2/4096:.2f}A = {((alt/4096)*(alt2/4096)):.2f}W")
            # print(f"Rail: {rail['name']} | Power: {alt/4096}V x {alt2/4096}A = {((alt/4096)*(alt2/4096)):.2f}W")
            print(f"Rail: {rail['name']} | Power: {decodedalt:.2f}V x {decodedalt2:.2f}A = {(decodedalt*decodedalt2):.2f}W")
            line += f"{decodedalt:.2f},{decodedalt2:.2f},{(decodedalt*decodedalt2):.2f},{alt},{alt2}"
    if file:
        with open("me.csv", "a") as f:
            # print(f"Writing line to me.csv: {line}")
            f.write(line + "\n")


def getReadingsBus(busNumber, safe = True):
    # safe = True means that we are threading and safe = False means we are not
    bus = smbus2.SMBus(busNumber)
    if not safe:
        readAll(bus, 0x8B, 0x8C)
        return # we want to get out of here
    try:
        while not stop_event.is_set() and safe:
            readAll(bus, 0x8B, 0x8C, file=True)
            time.sleep(0.25)
    except KeyboardInterrupt:
        stop_event.set()

def stringbuilder(args):
    return "".join(args)

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

def tripleLoop(initialvoltage, cwd, iter, step):
    print("==============================")
    print("========== Hi Maryam =========")
    print("==============================")


    subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
    subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)
    # runCommand("echo $XLNX_VART_FIRMWARE", cwd)
    # offload("v_0.85") # offload the files to the board
    # exit()

    volt = NOMINAL_VOLTAGE
    for dontuseme in range(1):
        print("==============================")
        print(f"Voltage: {volt:.2f} {dontuseme}")
        print("==============================")
        # setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, volt)
        imageNum = 10
        images = f"{imageNum}"
        exePath = "./layer_executables/conv1_caps_layer.exe"
        modelPath = "model/conv1.xmodel"
        imgpath = "img/MNIST/t10k-images-idx3-ubyte"
        firstOutput = f"/home/root/UV_outputs/conv1/v_{volt:.2f}"
        firstcmd = stringbuilder([exePath, " ", modelPath, " ", imgpath, " ", images, " ", firstOutput])

        exePath = "./layer_executables/primcaps_with_squash_layer.exe"
        modelPath = "model/primarycap_conv2d.xmodel"
        secondOutput = f"/home/root/UV_outputs/prim_caps/v_{volt:.2f}"
        thirdOutput = f"/home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}"
        convolutionalOutput = f"/home/root/convolutional_output_v_{volt:.2f}.txt"
        secondcmd = stringbuilder([exePath, " ", modelPath, " ", firstOutput, " ", images, " ", secondOutput, " ", thirdOutput, " ", convolutionalOutput])

        exePath = "./layer_executables/digit_caps_layer.exe"
        weights = "weights/new_digitcaps_weights.txt"
        digit_capsPath = f"/home/root/UV_outputs/digit_caps/v_{volt:.2f}"
        thirdcmd = stringbuilder([exePath, " ", weights, " ", thirdOutput, " ", digit_capsPath, " ", images])

        # cmb = firstcmd + ";" + secondcmd + ";" + thirdcmd
        # print(f"Running command: {cmb}")
        # we need them broken up
        subprocess.run(f"mkdir -p /home/root/UV_outputs/conv1/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/prim_caps/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/digit_caps/v_{volt:.2f}", shell=True)
        order = [0.85, 0.85, 0.85]

        subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
        subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if order[0]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if order[0]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(firstcmd, cwd)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if order[1]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if order[1]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(secondcmd, cwd)

        subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
        subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if order[2]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if order[2]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(thirdcmd, cwd)
        # clean up the other files

        # offload(f"v_{volt:.2f}") # offload the files to the board
        subprocess.run(f"rm -rf /home/root/UV_outputs/conv1/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/prim_caps/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/digit_caps/v_{volt:.2f}", shell=True)
        volt -= step
    stop()

def cmdBuilder(exepath, modelpath, xclpath, imgpath, weightspath, images, labelspath):
    return f"{exepath} {modelpath} {xclpath} {imgpath} {weightspath} {images} {labelspath}"

def main():

    # All constants
    cwd = "."

    EXE_PATH = "./bin/CapsuleNetwork.exe"
    MODEL_PATH = "model/partial_caps.xmodel"
    XCL_PATH = "../four_kernels.xclbin"
    IMG_PATH = "img/MNIST/t10k-images-idx3-ubyte"
    WEIGHTS_PATH = "weights/new_digitcaps_weights.txt"
    IMAGES = "1"
    LABELS_PATH = "img/MNIST/t10k-labels-idx1-ubyte"

    # The nomial voltage is 0.85
    ITER = 31
    STEP = 0.01

    # open and close me.csv
    with open("me.csv", "w") as f:
        pass

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
        elif mchoice == 99:
            exit()
        elif mchoice == 6:
            IMAGES = input("Please enter the number of images: ")
            if not IMAGES.isnumeric():
                raise Exception(f"{IMAGES} is not a valid number of images")
            ITER = int(input("Please enter the number of iterations (type: integer): "))
            STEP = float(input("Please enter the step size (type: float): "))
            print("==============================")
            print("====== Running Command =======")
            print("==============================")
        elif mchoice == 7:

            if isThreaded:
                monitorThread = threading.Thread(target=getReadingsBus, args=(4, True,), daemon=True)
                shellThread = threading.Thread(target=tripleLoop, args=(NOMINAL_VOLTAGE, cwd, ITER, STEP), daemon=True)
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



            setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal

            # scp -r ./UV_outputs/digit_caps/v_* beta@192.168.9.1:/home/beta/Desktop/Part-4-project/recovered/

            print("==============================")
            print("==========Finished============")
            print("==============================")

            # print("Copying files to board...")
            # print("scp -r ./UV_outputs/digit_caps/v_* beta@192.168.9.1:/home/beta/Desktop/Part-4-project/recovered/")
            print("scp -r ./me.csv beta@192.168.9.1:/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/")
            
            exit(1)
        elif mchoice == 8:
            tripleLoop(NOMINAL_VOLTAGE, cwd, ITER, STEP)
            print("==============================")
            print("==========Finished============")
            print("==============================")

            # print("Copying files to board...")
            # print("scp -r ./UV_outputs/digit_caps/v_* beta@192.168.9.1:/home/beta/Desktop/Part-4-project/recovered/")
            
            exit(1)

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