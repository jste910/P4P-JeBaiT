# import smbus2
# import time
# import threading
# import subprocess
# import argparse

# # constants
# BUS_NUMBER = 4
# VCCINT_RAIL = 0x13
# VCCBRAM_RAIL = 0x14
# VOLTAGE_RAIL = VCCINT_RAIL
# DESTINATION_REGISTER = 0x21
# ZCU102_NOM = 0.85
# NOMINAL_VOLTAGE = ZCU102_NOM

# BUS_LINE = smbus2.SMBus(BUS_NUMBER)

# # This is to pass the argument to switch between power advantage and UART
# parser = argparse.ArgumentParser(description='PA or UART')
# parser.add_argument('--threaded', type=str, required=False, help='see source for details')
# # parser.add_argument('--threaded', type=str, required=True, help='see source for details')
# # if true, this --threaded argument will run in a way to allow UART to capture the output
# # if false, this --threaded argument will run without being threaded to allow power advantage to capture the output

# args = parser.parse_args()
# print(f"Option: {args.threaded}")
# if args.threaded:
#     isThreaded = args.threaded.lower() == 'true'
#     print(f"isThreaded: {isThreaded} {type(isThreaded)}")
# else:
#     isThreaded = False # default
# # define out here
# stop_event = threading.Event()

# def readData(bus, device_address, location):
#     try:
#         # Read the data from the device
#         data = bus.read_word_data(device_address, location)
#         return data
#     except OSError as e:
#         print(f"Error reading from device at address {hex(device_address)}: {e}")
#         return None

# def readLoop(bus, rail, location):
#         alt = readData(bus, VOLTAGE_RAIL, location)
#         if alt is not None:
#             print(f"{location}: {hex(alt)} || {alt} Value: {alt/4096}V")

# def readAll(bus, voltageLocation, currentLocation):
#     alt = readData(bus, VOLTAGE_RAIL, voltageLocation)
#     alt2 = readData(bus, VOLTAGE_RAIL, currentLocation)
#     if alt is not None and alt2 is not None:
#         print(f"Power: {alt/4096:.2f}V x {alt2/4096:.2f}A = {(alt/4096)*(alt2/4096):.2f}W")
#         # print(f"Power: {alt/4096:.2f}V ({alt}) x {alt2/4096:.2f}A ({alt2})= {(alt/4096)*(alt2/4096):.2f}W") # debug


# def getReadingsBus(busNumber, safe = True):
#     # safe = True means that we are threading and safe = False means we are not
#     bus = smbus2.SMBus(busNumber)
#     if not safe:
#         readAll(bus, 0x8B, 0x8C)
#         return # we want to get out of here
#     try:
#         while not stop_event.is_set() and safe:
#             readAll(bus, 0x8B, 0x8C)
#             time.sleep(0.25)
#     except KeyboardInterrupt:
#         stop_event.set()

# def runCommand(cmd, cwd):
#     subprocess.run(cmd, shell=True, cwd=cwd)

# def stop():
#     stop_event.set()

# def undervoltingLoop(initialvoltage, cwd, cmd, iter, step):
#     volt = initialvoltage
#     for _ in range(iter):
#         print("==============================")
#         print(f"Voltage: {volt:.2f}")
#         print("==============================")
#         setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, volt)
#         runCommand(cmd, cwd)
#         volt -= step
#     setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal
#     stop()

# def runResNet18():
#     # hypothetically this does the same
#     cwd = "./Vitis-AI/examples/vai_library/samples/classification"
#     ResNet18Command = "./test_jpeg_classification resnet18_pt ~/Vitis-AI/examples/vai_library/samples/classification/images/002.JPEG"
#     NUM_STEPS = 28
#     step = 0.01
#     undervoltingLoop(NOMINAL_VOLTAGE, cwd=cwd, cmd = ResNet18Command, iter=NUM_STEPS, step=step)

# def runResNet50():
#     # hypothetically this does the same
#     cwd = "./Vitis-AI/examples/vai_runtime/resnet50"
#     resnet50cmd = "./resnet50 /usr/share/vitis_ai_library/models/resnet50/resnet50.xmodel"
#     NUM_STEPS = 28
#     step = 0.01
#     undervoltingLoop(NOMINAL_VOLTAGE, cwd=cwd, cmd = resnet50cmd, iter=NUM_STEPS, step=step)

# def runSqueezeNet():
#     # hypothetically this does the same
#     cwd = "./Vitis-AI/examples/vai_runtime/squeezenet_pytorch"
#     SqueezeNetcmd = "./squeezenet_pytorch /usr/share/vitis_ai_library/models/squeezenet_pt/squeezenet_pt.xmodel"
#     NUM_STEPS = 26
#     step = 0.01
#     undervoltingLoop(NOMINAL_VOLTAGE, cwd=cwd, cmd = SqueezeNetcmd, iter=NUM_STEPS, step=step)

# def runInception():
#     # hypothetically this does the same
#     cwd = "./Vitis-AI/examples/vai_runtime/inception_v1_mt_py"
#     Inceptioncmd = "/usr/bin/python3 inception_v1.py 1 /usr/share/vitis_ai_library/models/inception_v1_tf/inception_v1_tf.xmodel"
#     NUM_STEPS = 26
#     step = 0.01
#     undervoltingLoop(NOMINAL_VOLTAGE, cwd=cwd, cmd = Inceptioncmd, iter=NUM_STEPS, step=step)

# def runCompendium():

#     # open file
#     f = open("compendium.txt", "r")
#     for v in f:
#         # for each line in the file read and set the voltage to it
#         setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, float(v.strip()))  # reset back to normal
#         time.sleep(0.25) # change as needed
#     f.close()

#     setVoltage(BUS_LINE, VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE) # reset back to normal
#     stop()

# def setVoltage(bus, address, destination, voltageDecimal):
#     # This needs to be converted to a value between 0 and 4096 and written into hex
#     if voltageDecimal < 0 or voltageDecimal > 1: # out of bounds
#         raise Exception(f"Voltage must be between 0 and 1, entered voltage: {voltageDecimal}")
#     try:
#         bus.write_word_data(address, destination, (int(voltageDecimal*4096)))
#         return True
#     except OSError as e:
#         print(f"Error writing to device at address {hex(address)}: {e}")
#         return False

# def selectedModel(model, threaded=False):
#     if threaded:
#         if model=="ResNet50":
#             return runResNet50
#         elif model=="ResNet18":
#             return runResNet18
#         elif model=="SqueezeNet":
#             return runSqueezeNet
#         elif model=="Inception":
#             return runInception
#         elif model=="Compendium":
#             return runCompendium
#     else:
#         if model=="ResNet50":
#             return runResNet50()
#         elif model=="ResNet18":
#             return runResNet18()
#         elif model=="SqueezeNet":
#             return runSqueezeNet()
#         elif model=="Inception":
#             return runInception()
#         elif model=="Compendium":
#             return runCompendium()


#     raise Exception(f"Model {model} not supported")

# def main():

#     defaultmodel = "SqueezeNet"

#     print("=======================")
#     print("=== Model Selection ===")
#     print("1. Inception   ")
#     print("2. ResNet-18   ")
#     print("3. ResNet-50   ")
#     print("4. SqueezeNet  ")
#     print("5. Compendium  ")
#     print("=======================")
#     modelchoice = input(f"Please select a model number or \"\" to use {defaultmodel}: ")
#     if modelchoice.isnumeric(): # if it is numeric
#         mchoice = int(modelchoice)
#         if mchoice == 1:
#             model = "Inception"
#         elif mchoice == 2:
#             model = "ResNet18"
#         elif mchoice == 3:
#             model = "ResNet50"
#         elif mchoice == 4:
#             model = "SqueezeNet"
#         elif mchoice == 5:
#             model = "Compendium"
#         else:
#             raise Exception(f"{mchoice} is an invalid choice")
#     else: # if it is not numeric (either blank or other input)
#         print(f"Using default model: {defaultmodel}")
#         model = defaultmodel

#     print("==============================")
#     print(f"=== Using Model: {model} ===")
#     print("==============================")
#     shellCommand = "./test_performance_facedetect densebox_320_320 test_performance_facedetect.list -t 3 -s 20" # run with 3 threads for 20 seconds

#     setVoltage(smbus2.SMBus(BUS_NUMBER), VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)
#     directory = "./Vitis-AI/examples/vai_library/samples/facedetect"

#     if isThreaded:
#         # shellThread = threading.Thread(target=runCommand, args=(shellCommand,directory,))
#         monitorThread = threading.Thread(target=getReadingsBus, args=(4, True,), daemon=True)
#         shellThread = threading.Thread(target=selectedModel(model, threaded=True), daemon=True)
#         print("Threads started")
#         monitorThread.start()
#         shellThread.start()
#         try:
#             while monitorThread.is_alive() or shellThread.is_alive():
#                 monitorThread.join(timeout=1)
#                 shellThread.join(timeout=1)

#         except KeyboardInterrupt:
#             print("Shutting down")
#             # end all other processes
#             setVoltage(smbus2.SMBus(4), VOLTAGE_RAIL, DESTINATION_REGISTER, NOMINAL_VOLTAGE)  # reset back to normal
#             exit(1)
#     else: # not threaded
#         print("Running the selected model")
#         selectedModel(model)

#     print("==============================")
#     print("==========Finished============")
#     print("==============================")

# if __name__ == "__main__":
#     main()


import csv
import os
import subprocess
import threading
import time
from datetime import datetime

import smbus2

HOME = "/run/media/mmcblk0p1"
CAPSNET = f"{HOME}/capsnet"

# ZCU102 MAX15301 for PL VCCINT.
BUS_NUMBER = 4
VCCINT_REGULATOR_ADDRESS = 0x13

# PMBus commands.
PAGE = 0x00
VOUT_MODE = 0x20
VOUT_COMMAND = 0x21
READ_VOUT = 0x8B
READ_IOUT = 0x8C

# ---------------------------------------------------------------------------
# The five MAX15301-managed rails on the ZCU102.
#
# VCCINT is confirmed: bus 4, address 0x13, VOUT_COMMAND-controlled.
#
# The "address" and "page" values below for the other four rails are
# PLACEHOLDERS. The MAX15301 exposes multiple outputs either as separate
# I2C addresses on the bus (common on the ZCU102 power tree, since several
# MAX15301 devices are strapped to different addresses) or as PAGE-selected
# channels on a single PMBus device (if a rail is generated by a multi-phase
# / multi-output MAX15301 configuration). Confirm the real values against
# the ZCU102 schematic / power tree document and the MAX15301 datasheet
# before running this on hardware -- do NOT trust the placeholders.
#
# If a rail is a distinct I2C device, set "page" to None.
# If a rail is a PAGE-selected channel on a shared device, set "address" to
# that device's address and "page" to the channel number.
# ---------------------------------------------------------------------------
RAILS = [
    {
        "name": "VCCINT",
        "address": VCCINT_REGULATOR_ADDRESS,
        "page": None,
        "vout_exponent": -12,
    },
    {
        "name": "VCCOPSDDR504",
        "address": 0x14,  # PLACEHOLDER -- verify against ZCU102 power tree
        "page": None,
        "vout_exponent": -12,
    },
    {
        "name": "VCCAUX",
        "address": 0x15,  # PLACEHOLDER -- verify against ZCU102 power tree
        "page": None,
        "vout_exponent": -12,
    },
    {
        "name": "VCCDDRPLL",
        "address": 0x16,  # PLACEHOLDER -- verify against ZCU102 power tree
        "page": None,
        "vout_exponent": -12,
    },
    {
        "name": "VCCBRAM",
        "address": 0x17,  # PLACEHOLDER -- verify against ZCU102 power tree
        "page": None,
        "vout_exponent": -12,
    },
]

NOMINAL_VOLTAGE = 0.70
MIN_SAFE_VOLTAGE = 0.50
MAX_SAFE_VOLTAGE = 1.00
SAMPLE_INTERVAL_S = 0.25

stop_event = threading.Event()
measurement_active = threading.Event()
measurement_lock = threading.Lock()
pmbus_lock = threading.Lock()

latest_power_w = None
latest_rail_power_w = {rail["name"]: None for rail in RAILS}

energy_j = 0.0
rail_energy_j = {rail["name"]: 0.0 for rail in RAILS}
previous_sample_time_ns = None
previous_power_w = None
previous_rail_power_w = {rail["name"]: None for rail in RAILS}
power_samples = 0

measurement_start_ns = None
measurement_end_ns = None


def sign_extend(value, bits):
    """Sign-extend an integer encoded using the specified number of bits."""
    sign_bit = 1 << (bits - 1)
    return (value ^ sign_bit) - sign_bit


def decode_linear11(raw_word):
    """
    Decode a PMBus LINEAR11 value.

    Bits 15:11 contain a signed 5-bit exponent.
    Bits 10:0 contain a signed 11-bit mantissa.

    value = mantissa * 2**exponent
    """
    exponent = sign_extend((raw_word >> 11) & 0x1F, 5)
    mantissa = sign_extend(raw_word & 0x07FF, 11)
    return mantissa * (2.0 ** exponent)


def decode_vout(raw_word, exponent=-12):
    """
    Decode READ_VOUT for the ZCU102 MAX15301 VCCINT regulator.

    The device uses a fixed VOUT exponent of -12, so:
        voltage = raw_word / 4096
    """
    return raw_word * (2.0 ** exponent)


def set_voltage(voltage):
    if not MIN_SAFE_VOLTAGE <= voltage <= MAX_SAFE_VOLTAGE:
        raise ValueError(
            f"Requested voltage {voltage:.3f} V is outside the allowed "
            f"range {MIN_SAFE_VOLTAGE:.3f} V to {MAX_SAFE_VOLTAGE:.3f} V"
        )

    raw_command = int(round(voltage * 4096.0))

    with pmbus_lock:
        with smbus2.SMBus(BUS_NUMBER) as bus:
            bus.write_word_data(
                VCCINT_REGULATOR_ADDRESS,
                VOUT_COMMAND,
                raw_command,
            )


def read_word(bus, device_address, command):
    for attempt in range(3):
        try:
            with pmbus_lock:
                return bus.read_word_data(device_address, command)
        except OSError as error:
            if attempt == 2:
                print(
                    "PMBus read failed: "
                    f"bus={BUS_NUMBER}, "
                    f"device=0x{device_address:02X}, "
                    f"command=0x{command:02X}, "
                    f"error={error}"
                )
            time.sleep(0.02)

    return None


def select_page(bus, device_address, page):
    """Select a PMBus PAGE (channel) on a multi-output device.

    No-op if page is None, i.e. the rail lives on its own I2C address.
    """
    if page is None:
        return True

    for attempt in range(3):
        try:
            with pmbus_lock:
                bus.write_byte_data(device_address, PAGE, page)
            return True
        except OSError as error:
            if attempt == 2:
                print(
                    "PMBus PAGE select failed: "
                    f"bus={BUS_NUMBER}, "
                    f"device=0x{device_address:02X}, "
                    f"page={page}, "
                    f"error={error}"
                )
            time.sleep(0.02)

    return False


def read_rail(bus, rail):
    """Read voltage, current, and power for a single rail.

    Returns a dict with raw + decoded values, or None if the read failed.
    """
    address = rail["address"]
    page = rail["page"]

    if not select_page(bus, address, page):
        return None

    raw_voltage = read_word(bus, address, READ_VOUT)
    raw_current = read_word(bus, address, READ_IOUT)

    if raw_voltage is None or raw_current is None:
        return None

    voltage = decode_vout(raw_voltage, exponent=rail["vout_exponent"])
    current = decode_linear11(raw_current)
    power = voltage * current

    return {
        "name": rail["name"],
        "raw_voltage": raw_voltage,
        "raw_current": raw_current,
        "voltage_v": voltage,
        "current_a": current,
        "power_w": power,
    }


def read_all_rails(bus):
    """Read every configured rail. Returns a list of per-rail dicts, with
    None entries for rails that failed to read."""
    return [read_rail(bus, rail) for rail in RAILS]


def validate_pmbus_device():
    """
    Perform a small startup check before running measurements.

    Reads every configured rail once and sanity-checks the decoded values.
    This does not prove that the bus routing is correct, but it helps detect
    obvious communication and decoding problems -- and, importantly, catches
    a wrong placeholder address/page in RAILS before a long undervolting run.
    """
    print("\nPMBus startup check")
    print(f"Bus: /dev/i2c-{BUS_NUMBER}")

    any_failed = False

    with smbus2.SMBus(BUS_NUMBER) as bus:
        for rail in RAILS:
            address = rail["address"]
            page = rail["page"]

            raw_mode = None
            try:
                if select_page(bus, address, page):
                    with pmbus_lock:
                        raw_mode = bus.read_byte_data(address, VOUT_MODE)
            except OSError:
                pass

            reading = read_rail(bus, rail)

            page_str = "" if page is None else f", page={page}"
            print(
                f"\n{rail['name']}: address=0x{address:02X}{page_str}"
            )

            if reading is None:
                any_failed = True
                print(
                    f"  FAILED to read telemetry for {rail['name']}. "
                    "Check the address/page in RAILS against the ZCU102 "
                    "power tree and MAX15301 documentation."
                )
                continue

            if raw_mode is not None:
                print(f"  VOUT_MODE raw: 0x{raw_mode:02X}")

            print(f"  READ_VOUT raw: 0x{reading['raw_voltage']:04X}")
            print(f"  READ_IOUT raw: 0x{reading['raw_current']:04X}")
            print(f"  Decoded voltage: {reading['voltage_v']:.6f} V")
            print(f"  Decoded current: {reading['current_a']:.6f} A")
            print(f"  Calculated power: {reading['power_w']:.6f} W")

            if not 0.3 <= reading["voltage_v"] <= 2.0:
                any_failed = True
                print(
                    f"  WARNING: decoded voltage for {rail['name']} looks "
                    "implausible. Check the address/page and VOUT format."
                )

            if not 0.0 <= reading["current_a"] <= 100.0:
                any_failed = True
                print(
                    f"  WARNING: decoded current for {rail['name']} looks "
                    "implausible. Check the address/page and LINEAR11 "
                    "decoding."
                )

    if any_failed:
        raise RuntimeError(
            "One or more rails failed the PMBus startup check. Verify the "
            "RAILS configuration (address/page/exponent) against the "
            "ZCU102 schematic and MAX15301 documentation before running "
            "the undervolting loop."
        )


def reset_measurement_state():
    global energy_j
    global rail_energy_j
    global previous_sample_time_ns
    global previous_power_w
    global previous_rail_power_w
    global power_samples
    global measurement_start_ns
    global measurement_end_ns

    energy_j = 0.0
    rail_energy_j = {rail["name"]: 0.0 for rail in RAILS}
    previous_sample_time_ns = None
    previous_power_w = None
    previous_rail_power_w = {rail["name"]: None for rail in RAILS}
    power_samples = 0
    measurement_start_ns = None
    measurement_end_ns = None


def monitor_power(power_log):
    global latest_power_w
    global latest_rail_power_w
    global energy_j
    global rail_energy_j
    global previous_sample_time_ns
    global previous_power_w
    global previous_rail_power_w
    global power_samples

    new_file = not os.path.exists(power_log)

    with smbus2.SMBus(BUS_NUMBER) as bus, open(
        power_log,
        "a",
        newline="",
    ) as file:
        writer = csv.writer(file)

        if new_file:
            header = ["timestamp", "monotonic_time_ns"]
            for rail in RAILS:
                header += [
                    f"{rail['name']}_raw_voltage_hex",
                    f"{rail['name']}_raw_current_hex",
                    f"{rail['name']}_voltage_V",
                    f"{rail['name']}_current_A",
                    f"{rail['name']}_power_W",
                ]
            header += ["TOTAL_POWER_W", "measurement_active"]
            writer.writerow(header)

        while not stop_event.is_set():
            readings = read_all_rails(bus)
            now_ns = time.monotonic_ns()

            # Skip this sample entirely if any rail failed to read, so the
            # total power figure is never silently short a rail.
            if any(reading is None for reading in readings):
                time.sleep(SAMPLE_INTERVAL_S)
                continue

            total_power = sum(
                reading["power_w"] for reading in readings
            )

            latest_power_w = total_power
            latest_rail_power_w = {
                reading["name"]: reading["power_w"]
                for reading in readings
            }

            if measurement_active.is_set():
                with measurement_lock:
                    if (
                        previous_sample_time_ns is not None
                        and previous_power_w is not None
                    ):
                        dt_s = (
                            now_ns - previous_sample_time_ns
                        ) / 1e9

                        if dt_s >= 0.0:
                            energy_j += (
                                previous_power_w + total_power
                            ) * 0.5 * dt_s

                            for reading in readings:
                                name = reading["name"]
                                prev = previous_rail_power_w[name]
                                if prev is not None:
                                    rail_energy_j[name] += (
                                        prev + reading["power_w"]
                                    ) * 0.5 * dt_s

                    previous_sample_time_ns = now_ns
                    previous_power_w = total_power
                    previous_rail_power_w = {
                        reading["name"]: reading["power_w"]
                        for reading in readings
                    }
                    power_samples += 1

            row = [datetime.now().isoformat(), now_ns]
            for reading in readings:
                row += [
                    f"0x{reading['raw_voltage']:04X}",
                    f"0x{reading['raw_current']:04X}",
                    f"{reading['voltage_v']:.6f}",
                    f"{reading['current_a']:.6f}",
                    f"{reading['power_w']:.6f}",
                ]
            row += [
                f"{total_power:.6f}",
                int(measurement_active.is_set()),
            ]
            writer.writerow(row)
            file.flush()

            time.sleep(SAMPLE_INTERVAL_S)


def run_command(command, log_file):
    global energy_j
    global rail_energy_j
    global previous_sample_time_ns
    global previous_power_w
    global previous_rail_power_w
    global power_samples
    global measurement_start_ns
    global measurement_end_ns

    process = subprocess.Popen(
        command,
        cwd=CAPSNET,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    result = {
        "measurement_type": "ACTIVE_INFERENCE",
        "runs": 0,
        "reported_measurement_window_ms": 0.0,
        "active_window_ms": 0.0,
        "idle_window_ms": 0.0,
        "latency_ms": 0.0,
        "python_measurement_window_ms": 0.0,
        "energy_j": 0.0,
        "rail_energy_j": {rail["name"]: 0.0 for rail in RAILS},
        "power_samples": 0,
    }

    output = []

    if process.stdout is None:
        process.kill()
        raise RuntimeError("Failed to capture child-process output")

    for line in process.stdout:
        output.append(line)
        text = line.strip()

        if text == "MEASUREMENT_START":
            with measurement_lock:
                reset_measurement_state()
                measurement_start_ns = time.monotonic_ns()
                previous_sample_time_ns = measurement_start_ns
                previous_power_w = latest_power_w
                previous_rail_power_w = dict(latest_rail_power_w)

            measurement_active.set()

        elif text == "MEASUREMENT_END":
            end_ns = time.monotonic_ns()
            measurement_active.clear()

            with measurement_lock:
                measurement_end_ns = end_ns

                if (
                    previous_sample_time_ns is not None
                    and previous_power_w is not None
                ):
                    tail_dt_s = (
                        end_ns - previous_sample_time_ns
                    ) / 1e9

                    if tail_dt_s >= 0.0:
                        energy_j += previous_power_w * tail_dt_s

                        for name, prev in previous_rail_power_w.items():
                            if prev is not None:
                                rail_energy_j[name] += prev * tail_dt_s

                result["energy_j"] = energy_j
                result["rail_energy_j"] = dict(rail_energy_j)
                result["power_samples"] = power_samples

                if measurement_start_ns is not None:
                    result["python_measurement_window_ms"] = (
                        end_ns - measurement_start_ns
                    ) / 1e6

        elif text.startswith("MEASUREMENT_TYPE="):
            result["measurement_type"] = text.split("=", 1)[1]

        elif text.startswith("RUNS="):
            result["runs"] = int(text.split("=", 1)[1])

        elif text.startswith("ACTIVE_WINDOW_MS="):
            value = float(text.split("=", 1)[1])
            result["active_window_ms"] = value
            result["reported_measurement_window_ms"] = value

        elif text.startswith("IDLE_WINDOW_MS="):
            value = float(text.split("=", 1)[1])
            result["idle_window_ms"] = value
            result["reported_measurement_window_ms"] = value

        elif text.startswith("LATENCY_PER_INFERENCE_MS="):
            result["latency_ms"] = float(text.split("=", 1)[1])

    process.wait()
    measurement_active.clear()

    with open(log_file, "w") as file:
        file.writelines(output)

    if process.returncode != 0:
        child_output = "".join(output)
        print(child_output)
        raise RuntimeError(
            f"Inference failed with code {process.returncode}. "
            f"See {log_file}"
        )

    if measurement_start_ns is None or measurement_end_ns is None:
        raise RuntimeError(
            "The executable did not emit both MEASUREMENT_START and "
            "MEASUREMENT_END markers."
        )

    return result


def choose(prompt, options, default):
    print()
    for key, value in options.items():
        print(f"{key}. {value}")

    selected = input(f"{prompt} [default {default}]: ").strip()
    return selected or default


def build_command(model, images, repetitions, output_dir):
    xclbin = f"{HOME}/four_kernels_150MHz.xclbin"
    weights = f"{CAPSNET}/weights/new_digitcaps_weights.txt"
    mnist = f"{CAPSNET}/img/MNIST/t10k-images-idx3-ubyte"
    labels = f"{CAPSNET}/img/MNIST/t10k-labels-idx1-ubyte"
    intermediate = f"{CAPSNET}/intermediate_results"

    commands = {
        "1": [
            f"{CAPSNET}/bin/capsnet_full.exe",
            f"{CAPSNET}/model/partial_caps.xmodel",
            xclbin,
            mnist,
            weights,
            str(images),
            labels,
            str(repetitions),
            output_dir,
        ],
        "2": [
            f"{CAPSNET}/bin/conv1.exe",
            f"{CAPSNET}/model/conv1.xmodel",
            mnist,
            str(images),
            output_dir,
            str(repetitions),
        ],
        "3": [
            f"{CAPSNET}/bin/primaryCaps_conv2d.exe",
            f"{CAPSNET}/model/primarycap_conv2d.xmodel",
            f"{intermediate}/conv1_0.85V",
            str(images),
            output_dir,
            "convolutional_output.txt",
            str(repetitions),
        ],
        "4": [
            f"{CAPSNET}/bin/primarySquash.exe",
            xclbin,
            f"{intermediate}/primarycaps_0.85V",
            str(images),
            output_dir,
            "primarycaps_output.txt",
            str(repetitions),
        ],
        "5": [
            f"{CAPSNET}/bin/digitcaps.exe",
            xclbin,
            weights,
            f"{intermediate}/squash_0.85V",
            str(images),
            output_dir,
            "primary_squash_output.txt",
            str(repetitions),
        ],
        "6": [
            f"{CAPSNET}/bin/length.exe",
            xclbin,
            f"{intermediate}/digitcaps_0.85V",
            str(images),
            output_dir,
            "digitcaps_output.txt",
            str(repetitions),
        ],
        "7": [
            f"{CAPSNET}/bin/capsnet_idle.exe",
            f"{CAPSNET}/model/partial_caps.xmodel",
            xclbin,
            mnist,
            weights,
            str(images),
            labels,
            str(repetitions),
            output_dir,
        ],
    }

    return commands[model]


def undervolting_loop(
    model,
    images,
    repetitions,
    model_name,
    iterations,
    step,
    results_dir,
):
    summary_file = f"{results_dir}/energy_summary.csv"

    with open(summary_file, "w", newline="") as file:
        writer = csv.writer(file)
        header = [
            "step",
            "model",
            "commanded_voltage_V",
            "measurement_type",
            "runs",
            "power_samples",
        ]
        for rail in RAILS:
            header += [
                f"{rail['name']}_average_power_W",
                f"{rail['name']}_energy_J",
            ]
        header += [
            "average_power_W",
            "python_measurement_window_ms",
            "reported_measurement_window_ms",
            "active_window_ms",
            "idle_window_ms",
            "latency_per_inference_ms",
            "total_energy_J",
            "energy_per_inference_mJ",
        ]
        writer.writerow(header)

        for index in range(iterations):
            voltage = NOMINAL_VOLTAGE - index * step

            if voltage < MIN_SAFE_VOLTAGE:
                print(
                    f"Stopped before unsafe voltage {voltage:.2f} V"
                )
                break

            print(f"\nVoltage: {voltage:.2f} V")
            set_voltage(voltage)
            time.sleep(0.5)

            if model == "7":
                voltage_output_dir = results_dir
            else:
                voltage_output_dir = os.path.join(
                    results_dir,
                    "layer_outputs",
                    f"{voltage:.2f}V",
                )
                os.makedirs(voltage_output_dir, exist_ok=True)

            command = build_command(
                model,
                images,
                repetitions,
                voltage_output_dir,
            )

            print("Command:", " ".join(command))

            result = run_command(
                command,
                f"{results_dir}/inference_"
                f"{index:02d}_{voltage:.2f}V.txt",
            )

            # Use the Python-side interval because it matches the same
            # timestamps used for energy integration.
            duration_s = (
                result["python_measurement_window_ms"] / 1000.0
            )

            average_power = (
                result["energy_j"] / duration_s
                if duration_s > 0.0
                else 0.0
            )

            energy_per_inference = (
                result["energy_j"] / result["runs"] * 1000.0
                if result["runs"] > 0
                else 0.0
            )

            row = [
                index,
                model_name,
                f"{voltage:.2f}",
                result["measurement_type"],
                result["runs"],
                result["power_samples"],
            ]
            for rail in RAILS:
                rail_energy = result["rail_energy_j"][rail["name"]]
                rail_avg_power = (
                    rail_energy / duration_s if duration_s > 0.0 else 0.0
                )
                row += [f"{rail_avg_power:.6f}", f"{rail_energy:.6f}"]
            row += [
                f"{average_power:.6f}",
                f"{result['python_measurement_window_ms']:.6f}",
                f"{result['reported_measurement_window_ms']:.6f}",
                f"{result['active_window_ms']:.6f}",
                f"{result['idle_window_ms']:.6f}",
                f"{result['latency_ms']:.6f}",
                f"{result['energy_j']:.6f}",
                f"{energy_per_inference:.6f}",
            ]
            writer.writerow(row)
            file.flush()

            print(
                f"MEASUREMENT_TYPE={result['measurement_type']}"
            )
            print(f"POWER_SAMPLES={result['power_samples']}")
            print(
                "PYTHON_MEASUREMENT_WINDOW_MS="
                f"{result['python_measurement_window_ms']:.6f}"
            )
            print(
                "REPORTED_MEASUREMENT_WINDOW_MS="
                f"{result['reported_measurement_window_ms']:.6f}"
            )

            if result["measurement_type"] == "CONFIGURED_IDLE":
                print(
                    f"AVERAGE_IDLE_POWER_W={average_power:.6f}"
                )
                print(
                    f"IDLE_WINDOW_MS={result['idle_window_ms']:.6f}"
                )
                print(
                    f"IDLE_WINDOW_ENERGY_J={result['energy_j']:.6f}"
                )
            else:
                print(f"RUNS={result['runs']}")
                print(
                    f"AVERAGE_ACTIVE_POWER_W={average_power:.6f}"
                )
                print(
                    f"ACTIVE_WINDOW_MS={result['active_window_ms']:.6f}"
                )
                print(
                    "LATENCY_PER_INFERENCE_MS="
                    f"{result['latency_ms']:.6f}"
                )
                print(
                    f"TOTAL_ENERGY_J={result['energy_j']:.6f}"
                )
                print(
                    "ENERGY_PER_INFERENCE_mJ="
                    f"{energy_per_inference:.6f}"
                )


def main():
    models = {
        "1": "Full CapsNet",
        "2": "Conv1",
        "3": "PrimaryCaps Conv2D",
        "4": "PrimarySquash",
        "5": "DigitCaps",
        "6": "Length",
        "7": "Configured Idle",
    }

    default_repetitions = {
        "1": 1,
        "2": 100,
        "3": 25,
        "4": 55,
        "5": 4,
        "6": 2000,
        "7": 1,
    }

    model = choose("Select model", models, "2")
    if model not in models:
        raise ValueError("Invalid model selection")

    images = int(input("Number of images [default 50]: ") or 50)

    if model == "7":
        repetitions = 1
        print(
            "Configured-idle executable controls its own "
            "warm-up and idle measurement duration."
        )
    else:
        repetitions = int(
            input(
                "Repetitions "
                f"[default {default_repetitions[model]}]: "
            )
            or default_repetitions[model]
        )

    iterations = int(
        input("Voltage levels [default 28]: ") or 28
    )
    step = float(
        input("Voltage step [default 0.01]: ") or 0.01
    )

    model_tag = {
        "1": "full_capsnet",
        "2": "conv1",
        "3": "primarycaps_conv2d",
        "4": "primary_squash",
        "5": "digitcaps",
        "6": "length",
        "7": "configured_idle",
    }[model]

    results_dir = os.path.join(
        HOME,
        "results",
        (
            f"{model_tag}_"
            f"{images}img_"
            f"{repetitions}rep_"
            f"{iterations}levels_"
            f"{step:.3f}Vstep_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ),
    )

    os.makedirs(results_dir, exist_ok=True)

    print(f"\nModel: {models[model]}")
    print(f"Images: {images}")
    print(f"Repetitions: {repetitions}")
    print(f"Results: {results_dir}")

    stop_event.clear()
    measurement_active.clear()

    validate_pmbus_device()
    set_voltage(NOMINAL_VOLTAGE)
    time.sleep(0.5)

    monitor = threading.Thread(
        target=monitor_power,
        args=(f"{results_dir}/power_log.csv",),
        daemon=True,
    )
    monitor.start()

    try:
        undervolting_loop(
            model,
            images,
            repetitions,
            models[model],
            iterations,
            step,
            results_dir,
        )
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        measurement_active.clear()
        stop_event.set()

        try:
            set_voltage(NOMINAL_VOLTAGE)
            print(
                f"VCCINT restored to {NOMINAL_VOLTAGE:.2f} V"
            )
        except Exception as error:
            print(
                "WARNING: failed to restore nominal VCCINT: "
                f"{error}"
            )

        monitor.join(timeout=2.0)

    print("Finished")


if __name__ == "__main__":
    main()