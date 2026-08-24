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
VOUT_MODE = 0x20
VOUT_COMMAND = 0x21
READ_VOUT = 0x8B
READ_IOUT = 0x8C

NOMINAL_VOLTAGE = 0.85
MIN_SAFE_VOLTAGE = 0.57
MAX_SAFE_VOLTAGE = 1.00
SAMPLE_INTERVAL_S = 0.25

stop_event = threading.Event()
measurement_active = threading.Event()
measurement_lock = threading.Lock()
pmbus_lock = threading.Lock()

latest_power_w = None

energy_j = 0.0
previous_sample_time_ns = None
previous_power_w = None
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


def validate_pmbus_device():
    """
    Perform a small startup check before running measurements.

    This does not prove that the bus routing is correct, but it helps detect
    obvious communication and decoding problems.
    """
    with smbus2.SMBus(BUS_NUMBER) as bus:
        raw_mode = None
        try:
            with pmbus_lock:
                raw_mode = bus.read_byte_data(
                    VCCINT_REGULATOR_ADDRESS,
                    VOUT_MODE,
                )
        except OSError:
            pass

        raw_voltage = read_word(
            bus,
            VCCINT_REGULATOR_ADDRESS,
            READ_VOUT,
        )
        raw_current = read_word(
            bus,
            VCCINT_REGULATOR_ADDRESS,
            READ_IOUT,
        )

    if raw_voltage is None or raw_current is None:
        raise RuntimeError(
            "Unable to read VCCINT telemetry from the MAX15301 at "
            f"bus {BUS_NUMBER}, address 0x{VCCINT_REGULATOR_ADDRESS:02X}"
        )

    voltage = decode_vout(raw_voltage)
    current = decode_linear11(raw_current)
    power = voltage * current

    print("\nPMBus startup check")
    print(f"Bus: /dev/i2c-{BUS_NUMBER}")
    print(
        f"Device address: 0x{VCCINT_REGULATOR_ADDRESS:02X} "
        "(expected ZCU102 PL VCCINT regulator)"
    )

    if raw_mode is not None:
        print(f"VOUT_MODE raw: 0x{raw_mode:02X}")

    print(f"READ_VOUT raw: 0x{raw_voltage:04X}")
    print(f"READ_IOUT raw: 0x{raw_current:04X}")
    print(f"Decoded voltage: {voltage:.6f} V")
    print(f"Decoded current: {current:.6f} A")
    print(f"Calculated power: {power:.6f} W")

    if not 0.4 <= voltage <= 1.1:
        raise RuntimeError(
            f"Decoded VCCINT voltage {voltage:.6f} V is implausible. "
            "Check the I2C bus, PMBus device address, and VOUT format."
        )

    if current < 0.0 or current > 100.0:
        raise RuntimeError(
            f"Decoded VCCINT current {current:.6f} A is implausible. "
            "Check the I2C bus, device address, and LINEAR11 decoding."
        )


def reset_measurement_state():
    global energy_j
    global previous_sample_time_ns
    global previous_power_w
    global power_samples
    global measurement_start_ns
    global measurement_end_ns

    energy_j = 0.0
    previous_sample_time_ns = None
    previous_power_w = None
    power_samples = 0
    measurement_start_ns = None
    measurement_end_ns = None


def monitor_power(power_log):
    global latest_power_w
    global energy_j
    global previous_sample_time_ns
    global previous_power_w
    global power_samples

    new_file = not os.path.exists(power_log)

    with smbus2.SMBus(BUS_NUMBER) as bus, open(
        power_log,
        "a",
        newline="",
    ) as file:
        writer = csv.writer(file)

        if new_file:
            writer.writerow(
                [
                    "timestamp",
                    "monotonic_time_ns",
                    "raw_voltage_hex",
                    "raw_current_hex",
                    "voltage_V",
                    "current_A",
                    "power_W",
                    "measurement_active",
                ]
            )

        while not stop_event.is_set():
            raw_voltage = read_word(
                bus,
                VCCINT_REGULATOR_ADDRESS,
                READ_VOUT,
            )
            raw_current = read_word(
                bus,
                VCCINT_REGULATOR_ADDRESS,
                READ_IOUT,
            )

            if raw_voltage is not None and raw_current is not None:
                voltage = decode_vout(raw_voltage)
                current = decode_linear11(raw_current)
                power = voltage * current
                now_ns = time.monotonic_ns()

                latest_power_w = power

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
                                    previous_power_w + power
                                ) * 0.5 * dt_s

                        previous_sample_time_ns = now_ns
                        previous_power_w = power
                        power_samples += 1

                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        now_ns,
                        f"0x{raw_voltage:04X}",
                        f"0x{raw_current:04X}",
                        f"{voltage:.6f}",
                        f"{current:.6f}",
                        f"{power:.6f}",
                        int(measurement_active.is_set()),
                    ]
                )
                file.flush()

            time.sleep(SAMPLE_INTERVAL_S)


def run_command(command, log_file):
    global energy_j
    global previous_sample_time_ns
    global previous_power_w
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

                result["energy_j"] = energy_j
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
        writer.writerow(
            [
                "step",
                "model",
                "commanded_voltage_V",
                "measurement_type",
                "runs",
                "power_samples",
                "average_power_W",
                "python_measurement_window_ms",
                "reported_measurement_window_ms",
                "active_window_ms",
                "idle_window_ms",
                "latency_per_inference_ms",
                "total_energy_J",
                "energy_per_inference_mJ",
            ]
        )

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

            writer.writerow(
                [
                    index,
                    model_name,
                    f"{voltage:.2f}",
                    result["measurement_type"],
                    result["runs"],
                    result["power_samples"],
                    f"{average_power:.6f}",
                    f"{result['python_measurement_window_ms']:.6f}",
                    f"{result['reported_measurement_window_ms']:.6f}",
                    f"{result['active_window_ms']:.6f}",
                    f"{result['idle_window_ms']:.6f}",
                    f"{result['latency_ms']:.6f}",
                    f"{result['energy_j']:.6f}",
                    f"{energy_per_inference:.6f}",
                ]
            )
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
