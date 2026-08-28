#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "Accel_Wrapper3.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t INPUT_SIZE =
    wrapper_constants_v3::DIGITCAPS_INPUT_COUNT;

constexpr std::size_t WEIGHT_SIZE =
    wrapper_constants_v3::DIGITCAPS_WEIGHT_COUNT;

constexpr std::size_t OUTPUT_SIZE =
    wrapper_constants_v3::DIGITCAPS_OUTPUT_COUNT;

constexpr uint32_t WARMUP_RUNS = 10;

fs::path input_path(
    const fs::path& dir,
    uint32_t index,
    const std::string& filename)
{
    const std::string name = "img" + std::to_string(index);
    const fs::path flat = dir / (name + ".txt");

    return fs::exists(flat)
        ? flat
        : dir / name / filename;
}

std::vector<float> load_values(
    const fs::path& path,
    std::size_t count)
{
    std::ifstream file(path);
    std::vector<float> values(count);

    for (float& value : values)
        file >> value;

    return values;
}

void dump_output(
    const fs::path& path,
    const float* data)
{
    std::ofstream file(path);

    file << std::fixed
         << std::setprecision(10);

    for (std::size_t i = 0; i < OUTPUT_SIZE; ++i)
        file << data[i] << '\n';
}

int main(int argc, char* argv[])
{
    const std::string xclbin_path = argv[1];
    const fs::path weights_path = argv[2];
    const fs::path input_dir = argv[3];

    const uint32_t image_count =
        static_cast<uint32_t>(
            std::stoul(argv[4]));

    const fs::path output_dir = argv[5];

    const std::string input_filename =
        argc > 6
            ? argv[6]
            : "primary_squash_output.txt";

    const uint32_t repetitions =
        argc > 7
            ? static_cast<uint32_t>(
                  std::stoul(argv[7]))
            : 100;

    // ---------------------------------------------------------
    // Load weights
    // ---------------------------------------------------------
    const auto weights =
        load_values(
            weights_path,
            WEIGHT_SIZE);

    // ---------------------------------------------------------
    // Load all input images before measurement
    // ---------------------------------------------------------
    std::vector<float> inputs(
        static_cast<std::size_t>(image_count)
        * INPUT_SIZE);

    for (uint32_t i = 0; i < image_count; ++i) {

        const auto values =
            load_values(
                input_path(
                    input_dir,
                    i,
                    input_filename),
                INPUT_SIZE);

        std::copy(
            values.begin(),
            values.end(),
            inputs.begin()
                + static_cast<std::size_t>(i)
                  * INPUT_SIZE);
    }

    // ---------------------------------------------------------
    // Initialise accelerator
    // ---------------------------------------------------------
    Accel_Wrapper3 accelerator(
        xclbin_path);

    accelerator.initialise_digitcaps_kernel(
        weights.data());

    std::vector<float> output(
        OUTPUT_SIZE);

    // ---------------------------------------------------------
    // Warm-up
    // ---------------------------------------------------------
    for (uint32_t i = 0;
         i < WARMUP_RUNS;
         ++i)
    {
        accelerator.update_digitcaps_kernel(
            inputs.data());

        accelerator.run_digitcaps_kernel();

        accelerator.read_digitcaps_kernel(
            output.data());
    }

    // ---------------------------------------------------------
    // Buffer for final outputs
    // ---------------------------------------------------------
    std::vector<float> saved_output(
        static_cast<std::size_t>(image_count)
        * OUTPUT_SIZE);

    // ---------------------------------------------------------
    // Measure ONLY run_digitcaps_kernel()
    // ---------------------------------------------------------
    double total_kernel_ms = 0.0;

    std::cout
        << "MEASUREMENT_START"
        << std::endl;

    for (uint32_t repeat = 0;
         repeat < repetitions;
         ++repeat)
    {
        for (uint32_t i = 0;
             i < image_count;
             ++i)
        {
            const float* input =
                inputs.data()
                + static_cast<std::size_t>(i)
                  * INPUT_SIZE;

            // ---------------------------------------------
            // NOT timed:
            // CPU conversion + input transfer
            // ---------------------------------------------
            accelerator.update_digitcaps_kernel(
                input);

            // ---------------------------------------------
            // TIMED:
            // XRT launch + FPGA execution + wait
            // ---------------------------------------------
            const auto start =
                Clock::now();

            accelerator.run_digitcaps_kernel();

            const auto end =
                Clock::now();

            total_kernel_ms +=
                std::chrono::duration<
                    double,
                    std::milli>(
                        end - start)
                    .count();

            // ---------------------------------------------
            // NOT timed:
            // output transfer + fixed -> float conversion
            // ---------------------------------------------
            accelerator.read_digitcaps_kernel(
                output.data());

            // Save final repetition only
            if (repeat + 1 == repetitions) {

                std::copy(
                    output.begin(),
                    output.end(),
                    saved_output.begin()
                        + static_cast<std::size_t>(i)
                          * OUTPUT_SIZE);
            }
        }
    }

    std::cout
        << "MEASUREMENT_END"
        << std::endl;

    // ---------------------------------------------------------
    // Results
    // ---------------------------------------------------------
    const uint64_t runs =
        static_cast<uint64_t>(
            image_count)
        * repetitions;

    const double latency_per_inference_ms =
        total_kernel_ms
        / static_cast<double>(runs);

    std::cout
        << std::fixed
        << std::setprecision(6)

        << "RUNS="
        << runs
        << '\n'

        << "KERNEL_ACTIVE_WINDOW_MS="
        << total_kernel_ms
        << '\n'

        << "KERNEL_LATENCY_PER_INFERENCE_MS="
        << latency_per_inference_ms
        << '\n';

    // ---------------------------------------------------------
    // Save outputs after measurement
    // ---------------------------------------------------------
    fs::create_directories(
        output_dir);

    for (uint32_t i = 0;
         i < image_count;
         ++i)
    {
        dump_output(
            output_dir
                / ("img"
                   + std::to_string(i)
                   + ".txt"),

            saved_output.data()
                + static_cast<std::size_t>(i)
                  * OUTPUT_SIZE);
    }

    return 0;
}