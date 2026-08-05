#!/usr/bin/env python3

import math
import os
import json
import shutil
import struct
import numpy as np

NUM_DIGITS = 10
CAPSULE_DIM = 16
EXPECTED_VALUES = NUM_DIGITS * CAPSULE_DIM

def get_labels():
    with open("Josiah/t10k-labels-idx1-ubyte", "rb") as f:
        magic, num_items = struct.unpack(">II", f.read(8))
        labels = np.frombuffer(f.read(), dtype=np.uint8)
    print(labels.shape)
    return labels

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

    labels = get_labels()
    pwd = os.getcwd()

    # externalfolder = ["000", "100", "010", "001"]
    externalfolder = ["000", "100"]
    # externalfolder = ["000"]
    for j in externalfolder:
        f=open(f"Josiah/results/{j}.csv","w")
        # volts = 0.85
        for i in range(85, 54, -1):
            volts = f"{i/100:.2f}"
            input_dir = os.path.join(pwd, "Josiah", "recoveredbuthidden", j, f"v_{volts}")
            # print(f"Input directory: {input_dir}")
            # print the contents of the input directory
            # print("Contents of the input directory:")
            # for item in os.listdir(input_dir):
            #     print(item)
            # for item in os.listdir(output_dir):
            #     print(item)


            # txt_files = sorted([f for f in os.listdir(input_dir) if f.startswith("img") and f.endswith(".txt")])
            txt_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.startswith("img") and f.endswith(".txt")]

            if not txt_files:
                print("No img*.txt files found.")
                return
            ans_correct = 0
            ans_total = 0
            ans_counter = 0

            resultarray = []


            for file_path in txt_files:
                prediction, lengths = predict_digit(file_path)
                total = sum(lengths)
                if total > 0:
                    probabilities = [length / total for length in lengths]
                else:
                    probabilities = [0.0] * NUM_DIGITS

                # what number is this file?
                # print(file_path)
                file_number = os.path.basename(file_path).split("/")
                file_number = file_number[-1].replace("img", "").replace(".txt", "")
                # print(f"File: {file_path}, Predicted: {prediction}, File Number: {file_number}") # dbg

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

                if result["prediction"] == labels[int(file_number)]:
                    ans_correct += 1
                ans_total += 1
                ans_counter += 1
                resultarray.append(result)
            print(f"Correct: {ans_correct}/{ans_total} ({ans_correct/ans_total:.2%})")
            # f.write(f"Correct: {ans_correct}/{ans_total} ({ans_correct/ans_total:.2%})\n")
            f.write(f"{volts},{ans_correct},{ans_total},{ans_correct/ans_total:.2}\n")
        f.close()
                # output_path = os.path.join(output_dir, os.path.basename(file_path).replace(".txt", ".json"))

                # with open(output_path, "w") as f:
                #     json.dump(result, f, indent=4)
            # print(f"Results: {resultarray}")

if __name__ == "__main__":
    main()
    # copy all files from Josiah/recovered/ into Josiah/recoveredbuthidden/ and then delete the files from Josiah/recovered/
    # do this recursively for the folders present
    # source_dir = os.path.join(os.getcwd(), "Josiah", "recovered")
    # dest_dir = os.path.join(os.getcwd(), "Josiah", "recoveredbuthidden")
    # if not os.path.exists(dest_dir):
    #     os.makedirs(dest_dir)
    # for root, dirs, files in os.walk(source_dir):
    #     # Compute the relative path from the source directory
    #     rel_path = os.path.relpath(root, source_dir)
    #     # Create the corresponding directory in the destination
    #     dest_subdir = os.path.join(dest_dir, rel_path)
    #     if not os.path.exists(dest_subdir):
    #         os.makedirs(dest_subdir)
    #     for file in files:
    #         source_file = os.path.join(root, file)
    #         dest_file = os.path.join(dest_subdir, file)
    #         shutil.copy2(source_file, dest_file)
    #         os.remove(source_file)