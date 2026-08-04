import csv
import os
import subprocess
import threading
import time
from datetime import datetime

import smbus2

HOME = "/run/media/mmcblk0p1"
CAPSNET = f"{HOME}/capsnet"

BUS_NUMBER = 4
VOLTAGE_RAIL = 0x13
DESTINATION_REGISTER = 0x21
NOMINAL_VOLTAGE = 0.85
MIN_SAFE_VOLTAGE = 0.57
SAMPLE_INTERVAL_S = 0.25

stop_event = threading.Event()
measurement_active = threading.Event()
measurement_lock = threading.Lock()
pmbus_lock = threading.Lock()

latest_power_w = None
energy_j = 0.0
previous_time_ns = None
previous_power_w = None
power_samples = 0


def set_voltage(voltage):
    if not 0.0 <= voltage <= 1.0:
        raise ValueError("Voltage must be between 0 and 1 V")

    with pmbus_lock:
        with smbus2.SMBus(BUS_NUMBER) as bus:
            bus.write_word_data(
                VOLTAGE_RAIL,
                DESTINATION_REGISTER,
                int(voltage * 4096),
            )


def read_word(bus, command):
    for attempt in range(3):
        try:
            with pmbus_lock:
                return bus.read_word_data(
                    VOLTAGE_RAIL,
                    command,
                )
        except OSError as error:
            if attempt == 2:
                print(
                    f"PMBus read failed: "
                    f"rail=0x{VOLTAGE_RAIL:02x}, "
                    f"command=0x{command:02x}, "
                    f"error={error}"
                )
            time.sleep(0.02)

    return None


def monitor_power(power_log):
    global latest_power_w
    global energy_j
    global previous_time_ns
    global previous_power_w
    global power_samples

    new_file = not os.path.exists(power_log)

    with smbus2.SMBus(BUS_NUMBER) as bus, open(
        power_log, "a", newline=""
    ) as file:
        writer = csv.writer(file)

        if new_file:
            writer.writerow(
                [
                    "timestamp",
                    "voltage_V",
                    "current_A",
                    "power_W",
                    "measurement_active",
                ]
            )

        while not stop_event.is_set():
            raw_voltage = read_word(bus, 0x8B)
            raw_current = read_word(bus, 0x8C)

            if raw_voltage is not None and raw_current is not None:
                voltage = raw_voltage / 4096.0
                current = raw_current / 4096.0
                power = voltage * current
                now_ns = time.monotonic_ns()

                latest_power_w = power

                if measurement_active.is_set():
                    with measurement_lock:
                        if (
                            previous_time_ns is not None
                            and previous_power_w is not None
                        ):
                            dt_s = (now_ns - previous_time_ns) / 1e9
                            energy_j += (
                                previous_power_w + power
                            ) * 0.5 * dt_s

                        previous_time_ns = now_ns
                        previous_power_w = power
                        power_samples += 1

                writer.writerow(
                    [
                        datetime.now().isoformat(),
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
    global previous_time_ns
    global previous_power_w
    global power_samples

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
        "measurement_window_ms": 0.0,
        "active_window_ms": 0.0,
        "idle_window_ms": 0.0,
        "latency_ms": 0.0,
        "energy_j": 0.0,
        "power_samples": 0,
    }
    output = []

    for line in process.stdout:
        output.append(line)
        text = line.strip()

        if text == "MEASUREMENT_START":
            with measurement_lock:
                energy_j = 0.0
                previous_time_ns = time.monotonic_ns()
                previous_power_w = latest_power_w
                power_samples = 0
            measurement_active.set()

        elif text == "MEASUREMENT_END":
            end_ns = time.monotonic_ns()
            measurement_active.clear()

            with measurement_lock:
                if (
                    previous_time_ns is not None
                    and previous_power_w is not None
                ):
                    energy_j += previous_power_w * (
                        end_ns - previous_time_ns
                    ) / 1e9

                result["energy_j"] = energy_j
                result["power_samples"] = power_samples

        elif text.startswith("MEASUREMENT_TYPE="):
            result["measurement_type"] = text.split("=", 1)[1]

        elif text.startswith("RUNS="):
            result["runs"] = int(text.split("=", 1)[1])

        elif text.startswith("ACTIVE_WINDOW_MS="):
            value = float(text.split("=", 1)[1])
            result["active_window_ms"] = value
            result["measurement_window_ms"] = value

        elif text.startswith("IDLE_WINDOW_MS="):
            value = float(text.split("=", 1)[1])
            result["idle_window_ms"] = value
            result["measurement_window_ms"] = value

        elif text.startswith("LATENCY_PER_INFERENCE_MS="):
            result["latency_ms"] = float(
                text.split("=", 1)[1]
            )

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
                "voltage_V",
                "measurement_type",
                "runs",
                "power_samples",
                "average_power_W",
                "measurement_window_ms",
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
                print(f"Stopped before unsafe voltage {voltage:.2f} V")
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
                os.makedirs(
                    voltage_output_dir,
                    exist_ok=True,
                )

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

            duration_s = (
                result["measurement_window_ms"] / 1000.0
            )

            average_power = (
                result["energy_j"] / duration_s
                if duration_s
                else 0.0
            )

            energy_per_inference = (
                result["energy_j"] / result["runs"] * 1000.0
                if result["runs"]
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
                    f"{result['measurement_window_ms']:.6f}",
                    f"{result['active_window_ms']:.6f}",
                    f"{result['idle_window_ms']:.6f}",
                    f"{result['latency_ms']:.6f}",
                    f"{result['energy_j']:.6f}",
                    f"{energy_per_inference:.6f}",
                ]
            )
            file.flush()

            print(
                "MEASUREMENT_TYPE="
                f"{result['measurement_type']}"
            )
            print(f"POWER_SAMPLES={result['power_samples']}")

            if result["measurement_type"] == "CONFIGURED_IDLE":
                print(
                    "AVERAGE_IDLE_POWER_W="
                    f"{average_power:.6f}"
                )
                print(
                    "IDLE_WINDOW_MS="
                    f"{result['idle_window_ms']:.6f}"
                )
                print(
                    "IDLE_WINDOW_ENERGY_J="
                    f"{result['energy_j']:.6f}"
                )
            else:
                print(f"RUNS={result['runs']}")
                print(
                    "AVERAGE_ACTIVE_POWER_W="
                    f"{average_power:.6f}"
                )
                print(
                    "ACTIVE_WINDOW_MS="
                    f"{result['active_window_ms']:.6f}"
                )
                print(
                    "LATENCY_PER_INFERENCE_MS="
                    f"{result['latency_ms']:.6f}"
                )
                print(
                    "TOTAL_ENERGY_J="
                    f"{result['energy_j']:.6f}"
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
    iterations = int(input("Voltage levels [default 28]: ") or 28)
    step = float(input("Voltage step [default 0.01]: ") or 0.01)

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

    set_voltage(NOMINAL_VOLTAGE)

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
        set_voltage(NOMINAL_VOLTAGE)
        monitor.join(timeout=1)

    print("Finished")


if __name__ == "__main__":
    main()
