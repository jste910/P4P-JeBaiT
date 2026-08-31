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
    wrapper_constants_v3::PRIMARY_SQUASH_INPUT_COUNT;

constexpr std::size_t OUTPUT_SIZE =
    wrapper_constants_v3::PRIMARY_SQUASH_OUTPUT_COUNT;

constexpr uint32_t WARMUP_RUNS = 10;

fs::path input_path(
    const fs::path& dir,
    uint32_t index,
    const std::string& filename)
{
    const std::string name =
        "img" + std::to_string(index);

    const fs::path flat =
        dir / (name + ".txt");

    return fs::exists(flat)
        ? flat
        : dir / name / filename;
}

std::vector<float> load_input(
    const fs::path& path)
{
    std::ifstream file(path);

    std::vector<float> values(
        INPUT_SIZE);

    for (float& value : values)
        file >> value;

    return values;
}

void dump_output(
    const fs::path& path,
    const float* data)
{
    std::ofstream file(path);

    file
        << std::fixed
        << std::setprecision(10);

    for (std::size_t i = 0;
         i < OUTPUT_SIZE;
         ++i)
    {
        file << data[i] << '\n';
    }
}

int main(
    int argc,
    char* argv[])
{
    // ---------------------------------------------------------
    // Command-line arguments
    //
    // argv[1] = xclbin path
    // argv[2] = input directory
    // argv[3] = image count
    // argv[4] = output directory
    // argv[5] = input filename [optional]
    // argv[6] = repetitions    [optional]
    // ---------------------------------------------------------

    const std::string xclbin_path =
        argv[1];

    const fs::path input_dir =
        argv[2];

    const uint32_t image_count =
        static_cast<uint32_t>(
            std::stoul(argv[3]));

    const fs::path output_dir =
        argv[4];

    const std::string input_filename =
        argc > 5
            ? argv[5]
            : "primarycaps_output.txt";

    const uint32_t repetitions =
        argc > 6
            ? static_cast<uint32_t>(
                  std::stoul(argv[6]))
            : 100;

    // ---------------------------------------------------------
    // Load all inputs before measurement
    // ---------------------------------------------------------

    std::vector<float> inputs(
        static_cast<std::size_t>(
            image_count)
        * INPUT_SIZE);

    for (uint32_t i = 0;
         i < image_count;
         ++i)
    {
        const auto values =
            load_input(
                input_path(
                    input_dir,
                    i,
                    input_filename));

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

    accelerator
        .initialise_primary_squash_kernel();

    std::vector<float> output(
        OUTPUT_SIZE);

    std::vector<float> saved_output(
        static_cast<std::size_t>(
            image_count)
        * OUTPUT_SIZE);

    // ---------------------------------------------------------
    // Warm-up
    //
    // Warm-up includes:
    //   update
    //   kernel execution
    //   output readback
    //
    // Nothing here contributes to reported timing.
    // ---------------------------------------------------------

    for (uint32_t i = 0;
         i < WARMUP_RUNS;
         ++i)
    {
        accelerator
            .update_primary_squash_kernel(
                inputs.data());

        accelerator
            .run_primary_squash_kernel();

        accelerator
            .read_primary_squash_kernel(
                output.data());
    }

    // ---------------------------------------------------------
    // Measure ONLY run_primary_squash_kernel()
    //
    // Excluded:
    //   float -> fixed conversion
    //   input BO write
    //   H2D sync
    //   D2H sync
    //   BO read
    //   fixed -> float conversion
    //   output saving
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
            // NOT TIMED:
            // convert input + transfer to FPGA memory
            // ---------------------------------------------

            accelerator
                .update_primary_squash_kernel(
                    input);

            // ---------------------------------------------
            // TIMED:
            // XRT launch + FPGA execution + XRT wait
            // ---------------------------------------------

            const auto start =
                Clock::now();

            accelerator
                .run_primary_squash_kernel();

            const auto end =
                Clock::now();

            total_kernel_ms +=
                std::chrono::duration<
                    double,
                    std::milli>(
                        end - start)
                    .count();

            // ---------------------------------------------
            // NOT TIMED:
            // output sync + readback + conversion
            // ---------------------------------------------

            accelerator
                .read_primary_squash_kernel(
                    output.data());

            // ---------------------------------------------
            // Save final repetition only
            // ---------------------------------------------

            if (repeat + 1 == repetitions)
            {
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
    // Dump outputs after measurement
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