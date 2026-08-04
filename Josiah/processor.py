#!/usr/bin/env python3

import math
from pathlib import Path
import json


NUM_DIGITS = 10
CAPSULE_DIM = 16
EXPECTED_VALUES = NUM_DIGITS * CAPSULE_DIM


def predict_digit(file_path):
    """Read a DigitCaps output file and compute the predicted digit."""

    with open(file_path, "r") as f:
        values = [float(line.strip()) for line in f if line.strip()]

    if len(values) != EXPECTED_VALUES:
        raise ValueError(
            f"{file_path} contains {len(values)} values "
            f"(expected {EXPECTED_VALUES})."
        )

    lengths = []

    for digit in range(NUM_DIGITS):
        start = digit * CAPSULE_DIM
        capsule = values[start:start + CAPSULE_DIM]

        length = math.sqrt(sum(v * v for v in capsule))
        lengths.append(length)

    prediction = max(range(NUM_DIGITS), key=lambda d: lengths[d])

    return prediction, lengths


def main():

    input_dir = Path("./recovered/v_0.85")
    output_dir = Path("./UV_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Input directory: {input_dir}")
    # print the contents of the input directory
    print("Contents of the input directory:")
    for item in input_dir.iterdir():
        print(item)
    for item in output_dir.iterdir():
        print(item)
    # exit()


    txt_files = sorted(input_dir.glob("img*.txt"))

    if not txt_files:
        print("No img*.txt files found.")
        return

    for file_path in txt_files:


        prediction, lengths = predict_digit(file_path)

        total = sum(lengths)

        if total > 0:
            probabilities = [length / total for length in lengths]
        else:
            probabilities = [0.0] * NUM_DIGITS

        result = {
            "prediction": prediction,
            "winning_length": lengths[prediction],
            "capsule_lengths": {
                str(i): lengths[i]
                for i in range(NUM_DIGITS)
            },
            "normalised_probabilities": {
                str(i): probabilities[i]
                for i in range(NUM_DIGITS)
            }
        }

        output_path = output_dir / (file_path.stem + ".json")

        with open(output_path, "w") as f:
            json.dump(result, f, indent=4)


if __name__ == "__main__":
    main()