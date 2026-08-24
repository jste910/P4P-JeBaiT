import glob
import os
import time
import smbus2
import subprocess
import threading
from datetime import datetime
import pexpect
"""
DEFINES
"""
# Input output readings, these need to be confirmed
BUS_NUMBER = 4
VOLTAGE_RAIL = 0x13
DESTINATION_REGISTER = 0x21
ZCU102_NOM = 0.85
NOMINAL_VOLTAGE = ZCU102_NOM
BUS_LINE = smbus2.SMBus(BUS_NUMBER)
# define the stop event
stop_event = threading.Event()
bus = smbus2.SMBus(4)

CONV1EXEPATH = "./layer_executables/conv1_caps_layer.exe"
CONV1MODEL = "model/conv1.xmodel"
IMGPATH = "img/MNIST/t10k-images-idx3-ubyte"
PRIMCAPS_EXEPATH = "./layer_executables/primcaps_with_squash_layer.exe"
PRIMCAPS_MODEL = "model/primarycap_conv2d.xmodel"
DIGITCAPS_EXEPATH = "./layer_executables/digit_caps_layer.exe"
WEIGHTS_PATH = "weights/new_digitcaps_weights.txt"

ALL_RAILS = [{
    "name": "VCCINT",
    "address": 0x13,
    "vout_exponent": -12,
    "tags": "PMBUS"

},
{
    "name": "VCCBRAM",
    "address": 0x14,
    "vout_exponent": -12,
    "tags": "PMBUS"

},
{
    "name": "VCCAUX",
    "address": 0x15,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCC1V2",
    "address": 0x16,
    "vout_exponent": -12,
    "tags": "PMBUS"

}, {
    "name": "VCC3V3",
    "address": 0x17,
    "vout_exponent": -12,
    "tags": "PMBUS"

},
{
    "name": "VCCDJ_FMC",
    "address": 0x18,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCCPSINTFP",
    "address": 0x0A,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCCPSINTLP",
    "address": 0x0B,
    "vout_exponent": -12,
    "tags": "PMBUS"
    
},
{
    "name": "DDR4_DIMM_VDDQ",
    "address": 0x1D,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCCOPS",
    "address": 0x10,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "UTIL3V3",
    "address": 0x1A,
    "vout_exponent": -12,
    "tags": "PMBUS"

},
{
    "name": "UTIL5V0",
    "address": 0x1B,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCCOPS3",
    "address": "/sys/class/hwmon/hwmon10",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCPSDDRPLL",
    "address": "/sys/class/hwmon/hwmon11",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCINT",
    "address": "/sys/class/hwmon/hwmon12",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCBRAM",
    "address": "/sys/class/hwmon/hwmon13",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCAUX",
    "address": "/sys/class/hwmon/hwmon14",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCC1V2",
    "address": "/sys/class/hwmon/hwmon15",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCC3V3",
    "address": "/sys/class/hwmon/hwmon16",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "CADJ_FMC",
    "address": "/sys/class/hwmon/hwmon17",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "MGTAVCC",
    "address": "/sys/class/hwmon/hwmon18",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "MGTAVTT",
    "address": "/sys/class/hwmon/hwmon19",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCPSINTFP",
    "address": "/sys/class/hwmon/hwmon2",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCPSINTLP",
    "address": "/sys/class/hwmon/hwmon3",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCPSAUX",
    "address": "/sys/class/hwmon/hwmon4",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCPSPLL",
    "address": "/sys/class/hwmon/hwmon5",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "MGTRAVCC",
    "address": "/sys/class/hwmon/hwmon6",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "MGTRAVTT",
    "address": "/sys/class/hwmon/hwmon7",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCO_PSDDR_504",
    "address": "/sys/class/hwmon/hwmon8",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCOPS",
    "address": "/sys/class/hwmon/hwmon9",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCC",
    "address": "/sys/class/hwmon/hwmon0",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VTT",
    "address": "/sys/class/hwmon/hwmon1",
    "vout_exponent": -12,
    "tags": "HWMON"
}
]

selected_rails = ALL_RAILS

"""
GENERIC / UTILITY
"""

def cmdBuilder(exepath, modelpath, xclpath, imgpath, weightspath, images, labelspath):
    return f"{exepath} {modelpath} {xclpath} {imgpath} {weightspath} {images} {labelspath}"

def runCommand(cmd, cwd):
    subprocess.run(cmd, shell=True, cwd=cwd)

def stringbuilder(args):
    return "".join(args)

def stop():
    stop_event.set()

"""
MATHEMATICAL / CALCULATION FUNCTIONS
"""

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

"""
SMBUS / HWMON FUNCTIONS
"""

def readFile(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except:
        return None

def readData(bus, device_address, location):
    try:
        # Read the data from the device
        data = bus.read_word_data(device_address, location)
        return data
    except OSError as e:
        print(f"Error reading from device at address {hex(device_address)}: {e}")
        return 0xFFFF

def setVoltage(bus, address, destination, voltageDecimal):
    """
    :param bus: The bus that the sensor is connected to
    :param address: The address of the rail that we want to read
    :param destination: The actual value inside the rail (See datasheet)
    :param voltageDecimal: The voltage to be written to the rail AS A DECIMAL
    :return: None
    """

    if voltageDecimal < 0 or voltageDecimal > 1: # out of bounds
        raise Exception(f"Voltage must be between 0 and 1, entered voltage: {voltageDecimal}")
    try:
        bus.write_word_data(address, destination, (int(voltageDecimal*4096)))
        return True
    except OSError as e:
        print(f"Error writing to device at address {hex(address)}: {e}")
        return False

def readAll(bus, RAILS, file=False, quiet=False):
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not quiet:
        print(f"Timestamp: {datetime_now}")
    line = datetime_now + ","
    for rail in RAILS:
        if not quiet:
            print(f"Reading rail: {rail['name']}")
        if rail["tags"] == "HWMON":
            line += printSensorValues(f"{rail['address']}", quiet=quiet) # run until the stop event is set
        if rail["tags"] == "PMBUS":
            alt = readData(bus, rail["address"], 0x8B)  # voltage
            alt2 = readData(bus, rail["address"], 0x8C) # current
            if alt is not None and alt2 is not None:
                decodedalt = decodeVoltage(alt)
                decodedalt2 = decodeCurrent(alt2)
                if not quiet:
                    print(f"Rail: {rail['name']} | Power: {decodedalt:.2f}V x {decodedalt2:.2f}A = {(decodedalt*decodedalt2):.2f}W")
                line += f"{alt},{alt2},{0xFFFF},"
            else: # failed
                line += f"{0xFFFF},{0xFFFF},{0xFFFF},"

    if file:
        with open("me.csv", "a") as f:
            f.write(line + "\n")

def getReadingsBus(busNumber, safe = True, quiet=False):
    # safe = True means that we are threading and safe = False means we are not
    bus = smbus2.SMBus(busNumber)
    if not safe:
        readAll(bus, selected_rails, quiet=quiet)
        return # we want to get out of here
    try:
        while not stop_event.is_set() and safe:
            readAll(bus, selected_rails, file=True, quiet=quiet)
            time.sleep(0.25)
    except KeyboardInterrupt:
        stop_event.set()

def printSensorValues(rail, quiet=False):
    hwmon = rail["address"]
    name = rail["name"]
    if not quiet:
        print(f"\n=== {hwmon} ({name}) ===")
    # Possible sensor types to read
    sensor_types = ["in2", "curr1", "power1"]
    rst = ""
    for sensor_type in sensor_types:
        files = glob.glob(os.path.join(hwmon, f"{sensor_type}_input"))
        for file_path in files:
            value = readFile(file_path)
            if value:
                if not quiet:
                    unit = {
                        "in2": "mV",
                        "curr1": "mA",
                        "power1": "uW" # I think this is the more appropriate unit
                    }.get(sensor_type, "")
                    print(f"{sensor_type}_input: {int(value)} {unit}")
                rst += f"{int(value)},"
            else:
                rst += f"{0xFFFF},"
    return rst

"""
COMMUNICATIONS
"""

def pingHost(host, count=1, timeout=2):
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
    """
    Offload the specified file(s) to the host computer
    This is generally for preserving file space which is limited
    The file locations will need to be catered on a case by case basis
    adjust as necessary.
    """

    ipAddress = "192.168.9.1"
    user = "beta"

    fileLocationLocal = f"/home/root/UV_outputs/digit_caps/{lst}"
    dest = "/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/"
    cmd = f"scp -r {fileLocationLocal} {user}@{ipAddress}:{dest}"
    print(cmd)
    if not pingHost(ipAddress):
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

def undervoltingLoop(initialvoltage, cwd, cmd, iter, step): # keeping incase it because easier to use than tripleLoop
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

def tripleLoop(initialvoltage, cwd, imageNum, step, iterations, voltingOrder = ["X", "X", "X"]):
    print("==============================")
    print("========== Hi Maryam =========")
    print("==============================")


    subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
    subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)

    volt = NOMINAL_VOLTAGE
    for dontuseme in range(iterations):
        print("==============================")
        print(f"Voltage: {volt:.2f} {dontuseme}")
        print("==============================")

        firstOutput = f"/home/root/UV_outputs/conv1/v_{volt:.2f}"
        firstcmd = stringbuilder([CONV1EXEPATH, " ", CONV1MODEL, " ", IMGPATH, " ", f"{imageNum}", " ", firstOutput])

        secondOutput = f"/home/root/UV_outputs/prim_caps/v_{volt:.2f}"
        thirdOutput = f"/home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}"
        convolutionalOutput = f"/home/root/convolutional_output_v_{volt:.2f}.txt"
        secondcmd = stringbuilder([PRIMCAPS_EXEPATH, " ", PRIMCAPS_MODEL, " ", firstOutput, " ", f"{imageNum}", " ", secondOutput, " ", thirdOutput, " ", convolutionalOutput])

        digit_capsPath = f"/home/root/UV_outputs/digit_caps/v_{volt:.2f}"
        thirdcmd = stringbuilder([DIGITCAPS_EXEPATH, " ", WEIGHTS_PATH, " ", thirdOutput, " ", digit_capsPath, " ", f"{imageNum}"])
        subprocess.run(f"mkdir -p /home/root/UV_outputs/conv1/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/prim_caps/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}", shell=True)
        subprocess.run(f"mkdir -p /home/root/UV_outputs/digit_caps/v_{volt:.2f}", shell=True)

        subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
        subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if voltingOrder[0]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if voltingOrder[0]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(firstcmd, cwd)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if voltingOrder[1]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if voltingOrder[1]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(secondcmd, cwd)

        subprocess.run("export XLNX_VART_FIRMWARE=\"/run/media/mmcblk0p1/four_kernels.xclbin\"", shell=True)
        subprocess.run("echo $XLNX_VART_FIRMWARE", shell=True)

        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt if voltingOrder[2]=="X" else NOMINAL_VOLTAGE))
        print(f'Voltage set to: {(volt if voltingOrder[2]=="X" else NOMINAL_VOLTAGE):.2f}V')
        runCommand(thirdcmd, cwd)
        # clean up the other files

        offload(f"v_{volt:.2f}") # offload the files to the board
        subprocess.run(f"rm -rf /home/root/UV_outputs/conv1/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/prim_caps/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/prim_caps_squash/v_{volt:.2f}", shell=True)
        subprocess.run(f"rm -rf /home/root/UV_outputs/digit_caps/v_{volt:.2f}", shell=True)
        volt -= step
    stop()


def main():

    # All constants
    cwd = "."

    IMAGES = "1"
    # The nomial voltage is 0.85
    ITER = 31
    STEP = 0.01

    # open and close me.csv
    with open("me.csv", "w") as f:
        line = f"Timestamp,"
        for r in selected_rails:
            line += f"[{r['tags']}] {r['name']} Voltage,"
            line += f"[{r['tags']}] {r['name']} Current,"
            line += f"[{r['tags']}] {r['name']} Power,"
        f.write(line + "\n")

    setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # set to nominal of 0.85V

    print("=======================")
    print("=== Model Selection ===")
    print("1. 1 Image")
    print("2. 10 Images")
    print("3. 25 Image")
    print("4. 100 Image")
    print("5. 1000 Image")
    print("6. Custom Amount")
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
            print("WARNING: This has not been tested and may crash the board due to memory issues. Please use with caution.")
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

        else:
            raise Exception(f"{mchoice} is an invalid choice")


    else: # if it is not numeric (either blank or other input)
        print(f"Using 10 images as default")
        IMAGES = "10"

    monitorThread = threading.Thread(target=getReadingsBus, args=(4, True, True), daemon=True)
    shellThread = threading.Thread(target=tripleLoop, args=(NOMINAL_VOLTAGE, cwd, IMAGES, STEP, ITER, ["X", "X", "X"]), daemon=True)
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
        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)  # reset back to normal
        exit(1)

    setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal

    print("==============================")
    print("==========Finished============")
    print("==============================")

    try:
        cmd ="scp -r ./me.csv beta@192.168.9.1:/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/"
        print(f"Executing command: {cmd}")

        child = pexpect.spawn(cmd)
        child.expect('password:')
        child.sendline(' ')
        for line in child: # progress bar
            print(f"Line: {line.decode('utf-8').strip()}")

        print("Copied successfully")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()