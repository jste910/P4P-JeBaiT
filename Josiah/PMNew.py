import glob
import os
import time
import smbus2
import subprocess
import threading
from datetime import datetime
import time
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

CAPSNETEXE = "./bin/capsnet_full.exe"
CONV1EXE = "./bin/conv1.exe"
CONV2DEXE = "./bin/primaryCaps_conv2d.exe"
PRIMARYSQUASHEXE = "./bin/primarySquash.exe"
DIGITCAPSEXE = "./bin/digitcaps.exe"
LENGTHEXE = "./bin/length.exe"

PARTIALCAPSMODEL = "model/partial_caps.xmodel"
CONV1MODEL = "model/conv1.xmodel"
CONV2DMODEL = "model/primarycap_conv2d.xmodel"

XCLBIN = "../dpu.xclbin"
IMG_PATH = "img/MNIST/t10k-images-idx3-ubyte"
WEIGHTS_PATH = "weights/new_digitcaps_weights.txt"
images = "50"
LABEL_PATH = "img/MNIST/t10k-labels-idx1-ubyte"
RERUN = "1"

INFEXE = "./bin/digitcaps_v3.exe" # missing exe
ALT_WEIGHTS_PATH = "weights/new_digitcaps_weight_fixed7_1.bin"
SWINF = "./bin/sw_digitcaps.exe"
INITEXE = "./bin/digitcaps_init_v3.exe"
UPDATEEXE = "./bin/digitcaps_update_v3.exe"
RUNEXE = "./bin/digitcaps_run_v3.exe"
READEXE = "./bin/digitcaps_read_v3.exe"

fullcapsoutput = "full_capsnet"

conv1folder = "/home/root/UV_outputs/intermediate_results/conv1"
primarycapsfolder = "/home/root/UV_outputs/intermediate_results/primarycaps"
squashfolder = "intermediate_results/squash_0.85V"
digitcapsfolder = "/home/root/UV_outputs/intermediate_results/digitcaps"
lengthfolder = "intermediate_results/length"

conv2dtxt = "convolutional_output.txt"
primarycapstxt = "primarycaps_output.txt"
primarysquashtxt = "primary_squash_output.txt"
digitcapstxt = "digitcaps_output.txt"

filename = "log.txt"
FREQUENCY = "0"

ALL_RAILS = [
{
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

selected_rails = [
{
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
    "name": "VCCPSINTFP",
    "address": 0x0A,
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
    "name": "VCCPSINTLP",
    "address": 0x0B,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
{
    "name": "VCCO_PSDDR_504",
    "address": "/sys/class/hwmon/hwmon8",
    "vout_exponent": -12,
    "tags": "HWMON"
},
{
    "name": "VCCAUX",
    "address": 0x15,
    "vout_exponent": -12,
    "tags": "PMBUS"
},
]

"""
GENERIC / UTILITY
"""

def cmdBuilder(exepath, modelpath, xclpath, imgpath, weightspath, images, labelspath):
    return f"{exepath} {modelpath} {xclpath} {imgpath} {weightspath} {images} {labelspath}"

def runCommand(cmd, cwd):
    # subprocess.run(cmd, shell=True, cwd=cwd)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)

    for line in process.stdout:
        text = line.decode('utf-8').strip()
        print(f"[{time.monotonic_ns()}] {text}")
        with open(filename, "a") as f:
            f.write(f"[{time.monotonic_ns()}] {text}\n")
    process.wait()  # Wait for the process to finish


def stringbuilder(args):
    return "".join(args)

def stop():
    stop_event.set()

def stringme(v):
    return f"{v[0]}{v[1]}{v[2]}{v[3]}{v[4]}"


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
    datetime_now = time.monotonic_ns()
    # print(f"Timestamp: {time.monotonic_ns()}")
    line = str(datetime_now) + ","

    for rail in RAILS:
        if not quiet:
            print(f"Reading rail: {rail['name']}")
        if rail["tags"] == "HWMON":
            line += printSensorValues(rail, quiet=quiet) # run until the stop event is set
        if rail["tags"] == "PMBUS":
            alt = readData(bus, rail["address"], 0x8B)  # voltage
            alt2 = readData(bus, rail["address"], 0x8C) # current
            alt3 = readData(bus, rail["address"], 0x8D) # temperature
            if alt is not None and alt2 is not None and alt3 is not None:
                decodedalt = decodeVoltage(alt)
                decodedalt2 = decodeCurrent(alt2)
                decodedalt3 = decodeCurrent(alt3)
                if not quiet:
                    print(f"Rail: {rail['name']} | Power: {decodedalt:.2f}V x {decodedalt2:.2f}A = {(decodedalt*decodedalt2):.2f}W and {decodedalt3}")
                line += f"{alt},{alt2},{alt3},{65535}"
            else: # failed
                line += f"{0xFFFF},{0xFFFF},{0xFFFF},{0xFFFF}"

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
            time.sleep(0.125) # 8Hz
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
    
def offload(lst, file=False):
    """
    Offload the specified file(s) to the host computer
    This is generally for preserving file space which is limited
    The file locations will need to be catered on a case by case basis
    adjust as necessary.
    """

    ipAddress = "192.168.9.1"
    user = "beta"

    fileLocationLocal = lst
    dest = "/home/beta/Desktop/P4P-JeBaiT/Josiah/recovered/"


    if file:
        cmd = f"scp {fileLocationLocal} {user}@{ipAddress}:{dest}"
    else:
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

    except Exception as e:
        print(f"Error: {e}")

def undervoltingLoop(cwd, img, step, iter): # keeping incase it because easier to use than seperatedLoop

    volt = NOMINAL_VOLTAGE
    for _ in range(iter):
        print("==============================")
        print(f"Voltage: {volt:.2f}")
        print("==============================")
        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, volt)
        runCommand(f"{CAPSNETEXE} {PARTIALCAPSMODEL} {XCLBIN} {IMG_PATH} {WEIGHTS_PATH} {img} {LABEL_PATH} {RERUN} {fullcapsoutput}", cwd)
        # rename and move
        subprocess.run(f"mv {fullcapsoutput}/capsnet_length_output.txt {fullcapsoutput}/full_{volt:.2f}V.txt", shell=True)
        offload(f"{fullcapsoutput}/full_{volt:.2f}V.txt", file=True) # offload the files to the board
        volt -= step
    setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal
    stop()

def seperatedLoop(cwd, img, step, iter, version=3):
    print("==============================")
    print("========== Hi Maryam =========")
    print("==============================")

    volt = NOMINAL_VOLTAGE
    for dontuseme in range(iter):
        print("==============================")
        print(f"Voltage: {volt:.2f} {dontuseme}")
        print("==============================")

        if (version == 1):
            ALT_WEIGHTS_PATH = "weights/new_digitcaps_weights_fixed32_16.bin"
        elif (version == 2):
            ALT_WEIGHTS_PATH = "weights/new_digitcaps_weights_int8.bin"
        elif (version == 3):
            ALT_WEIGHTS_PATH = "weights/new_digitcaps_weight_fixed7_1.bin"
        else:
            print("ERROR INVALID")
            exit()

        subprocess.run(f"mkdir -p {lengthfolder}/{volt:.2f}V", shell=True)
        # write a block of text to the filename
        global filename
        filename = f"{lengthfolder}/{volt:.2f}V/log.txt"
        with open(filename, "w") as f:
            f.write(f"ARCHITECTURE=v{version}\n")
            f.write(f"FREQUENCY={FREQUENCY}MHz\n")
            f.write(f"TARGET_VOLTAGE={volt:.2f}V\n")
            f.write(f"WEIGHTS={ALT_WEIGHTS_PATH}\n")
            f.write(f"NUM_IMAGES={img}\n")

        print("==============================")
        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, (volt))
        print(f'Voltage set to: {volt:.2f}V')
        digitexe = f"./bin/digitcaps_v{version}.exe {XCLBIN} {ALT_WEIGHTS_PATH} {squashfolder} {img} {lengthfolder}/{volt:.2f}V out.txt 1"
        print(f"Running {digitexe}")
        runCommand(digitexe, cwd)
        setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)
        print(f'Voltage set to: {volt:.2f}V')

        with open(f"{lengthfolder}/{volt:.2f}V/log.txt", "a") as f:
            f.write(f"STATUS=COMPLETED\n")

        offload(f"{lengthfolder}/{volt:.2f}V/", file=False) # offload the files to the board

        subprocess.run(f"rm -rf {lengthfolder}/{volt:.2f}V", shell=True) # remove the files from the board
        volt -= step
    stop()


def main():

    # All constants
    cwd = "."

    IMAGES = "50"
    # The nomial voltage is 0.85
    ITER = 31
    STEP = 0.01

    # open and close me.csv
    with open("me.csv", "w") as f:
        line = f"Timestamp,"
        for r in selected_rails:
            line += f"[{r['tags']}] {r['name']} Voltage,"
            line += f"[{r['tags']}] {r['name']} Current,"
            line += f"[{r['tags']}] {r['name']} Temperature,"
            line += f"[{r['tags']}] {r['name']} Power,"
        f.write(line + "\n")

    setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # set to nominal of 0.85V

    print("=======================")
    print("=== Model Selection ===")
    print("1. Digitcaps Version 1 10 Images (TEST)")
    print("2. Digitcaps Version 1 1000 Images")
    print("3. Digitcaps Version 2 10 Images (TEST)")
    print("4. Digitcaps Version 2 1000 Images")
    print("5. Digitcaps Version 3 10 Images (TEST)")
    print("6. Digitcaps Version 3 1000 Images")
    print("=======================")
    modelchoice = input(f"Please enter your choice: ")
    if modelchoice.isnumeric(): # if it is numeric
        mchoice = int(modelchoice)
        if mchoice == 1:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 10, STEP, 5, 1), daemon=True)
        elif mchoice == 2:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 1000, STEP, ITER, 1), daemon=True)
        elif mchoice == 3:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 10, STEP, 5, 2), daemon=True)
        elif mchoice == 4:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 1000, STEP, ITER, 2), daemon=True)
        elif mchoice == 5:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 10, STEP, 5, 3), daemon=True)
        elif mchoice == 6:
            shellThread = threading.Thread(target=seperatedLoop, args=(cwd, 1000, STEP, ITER, 3), daemon=True)
        elif mchoice == 99:
            exit()
        else:
            raise Exception(f"{mchoice} is an invalid choice")


    else: # if it is not numeric (either blank or other input)
        print("No valid input detected, exiting...")
        exit()

    # find out the other information about the board
    global FREQUENCY
    FREQUENCY = input(f"Please enter the frequency of the board: ")
    

    monitorThread = threading.Thread(target=getReadingsBus, args=(4, True, True), daemon=True)
    print("Threads started")
    start = time.monotonic_ns()
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


    # don't move me.csv yet
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

    end = time.monotonic_ns()
    print(f"All done in {end - start} ns or {(end - start)/1e9} seconds")


if __name__ == "__main__":
    main()