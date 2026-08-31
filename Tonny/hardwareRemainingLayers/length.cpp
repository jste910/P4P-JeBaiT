#include <algorithm>
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

constexpr std::size_t INPUT_SIZE = wrapper_constants_v3::CAPSNET_LENGTH_INPUT_COUNT;
constexpr std::size_t OUTPUT_SIZE = wrapper_constants_v3::CAPSNET_LENGTH_OUTPUT_COUNT;
constexpr uint32_t WARMUP_RUNS = 10;

fs::path input_path(const fs::path& dir, uint32_t index, const std::string& filename)
{
    const std::string name = "img" + std::to_string(index);
    const fs::path flat = dir / (name + ".txt");
    return fs::exists(flat) ? flat : dir / name / filename;
}

std::vector<float> load_input(const fs::path& path)
{
    std::ifstream file(path);
    std::vector<float> values(INPUT_SIZE);
    for (float& value : values) file >> value;
    return values;
}

void dump_output(const fs::path& path, const float* data)
{
    std::ofstream file(path);
    file << std::fixed << std::setprecision(10);
    for (std::size_t i = 0; i < OUTPUT_SIZE; ++i) file << data[i] << '\n';
}

int main(int argc, char* argv[])
{
    const std::string xclbin_path = argv[1];
    const fs::path input_dir = argv[2];
    const uint32_t image_count = static_cast<uint32_t>(std::stoul(argv[3]));
    const fs::path output_dir = argv[4];
    const std::string input_filename = argc > 5 ? argv[5] : "digitcaps_output.txt";
    const uint32_t repetitions = argc > 6 ? static_cast<uint32_t>(std::stoul(argv[6])) : 100;

    std::vector<float> inputs(static_cast<std::size_t>(image_count) * INPUT_SIZE);

    for (uint32_t i = 0; i < image_count; ++i) {
        const auto values = load_input(input_path(input_dir, i, input_filename));
        std::copy(values.begin(), values.end(), inputs.begin() + static_cast<std::size_t>(i) * INPUT_SIZE);
    }

    Accel_Wrapper3 accelerator(xclbin_path);
    accelerator.initialise_capsnet_length_kernel();

    std::vector<float> output(OUTPUT_SIZE);
    std::vector<float> saved_output(static_cast<std::size_t>(image_count) * OUTPUT_SIZE);

    for (uint32_t i = 0; i < WARMUP_RUNS; ++i) {
        accelerator.update_capsnet_length_kernel(inputs.data());
        accelerator.run_capsnet_length_kernel();
        accelerator.read_capsnet_length_kernel(output.data());
    }

    double total_stage_ms = 0.0;

    std::cout << "MEASUREMENT_START" << std::endl;

    for (uint32_t repeat = 0; repeat < repetitions; ++repeat) {
        for (uint32_t i = 0; i < image_count; ++i) {
            const float* input = inputs.data() + static_cast<std::size_t>(i) * INPUT_SIZE;

            const auto start = Clock::now();

            accelerator.update_capsnet_length_kernel(input);
            accelerator.run_capsnet_length_kernel();
            accelerator.read_capsnet_length_kernel(output.data());

            const auto end = Clock::now();

            total_stage_ms += std::chrono::duration<double, std::milli>(end - start).count();

            if (repeat + 1 == repetitions) {
                std::copy(output.begin(), output.end(), saved_output.begin() + static_cast<std::size_t>(i) * OUTPUT_SIZE);
            }
        }
    }

    std::cout << "MEASUREMENT_END" << std::endl;

    const uint64_t runs = static_cast<uint64_t>(image_count) * repetitions;

    std::cout << std::fixed << std::setprecision(6)
              << "RUNS=" << runs << '\n'
              << "STAGE_ACTIVE_WINDOW_MS=" << total_stage_ms << '\n'
              << "STAGE_LATENCY_PER_INFERENCE_MS=" << total_stage_ms / runs << '\n';

    fs::create_directories(output_dir);

    for (uint32_t i = 0; i < image_count; ++i) {
        dump_output(output_dir / ("img" + std::to_string(i) + ".txt"),
                    saved_output.data() + static_cast<std::size_t>(i) * OUTPUT_SIZE);
    }

    return 0;
}