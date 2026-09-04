#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "DigitCaps.h"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t INPUT_SIZE = DIGIT_CAPS_INPUT_CAPSULES * DIGIT_CAPS_INPUT_DIM_CAPSULE;
constexpr std::size_t WEIGHT_SIZE = DIGIT_CAPS_NUM_DIGITS * DIGIT_CAPS_INPUT_CAPSULES * DIGIT_CAPS_DIM_CAPSULE * DIGIT_CAPS_INPUT_DIM_CAPSULE;
constexpr std::size_t OUTPUT_SIZE = DIGIT_CAPS_NUM_DIGITS * DIGIT_CAPS_DIM_CAPSULE;
constexpr uint32_t WARMUP_RUNS = 10;

fs::path input_path(const fs::path& dir, uint32_t index, const std::string& filename)
{
    const std::string name = "img" + std::to_string(index);
    const fs::path flat = dir / (name + ".txt");
    return fs::exists(flat) ? flat : dir / name / filename;
}

std::vector<float> load_values(const fs::path& path, std::size_t count)
{
    std::ifstream file(path);

    if (!file) {
        throw std::runtime_error("Cannot open input file: " + path.string());
    }

    std::vector<float> values(count);

    for (std::size_t i = 0; i < count; ++i) {
        if (!(file >> values[i])) {
            throw std::runtime_error("Not enough values in file: " + path.string());
        }
    }

    return values;
}

void dump_output(const fs::path& path, const float* data)
{
    std::ofstream file(path);

    if (!file) {
        throw std::runtime_error("Cannot create output file: " + path.string());
    }

    file << std::fixed << std::setprecision(10);

    for (std::size_t i = 0; i < OUTPUT_SIZE; ++i) {
        file << data[i] << '\n';
    }
}

int main(int argc, char* argv[])
{
    if (argc < 5 || argc > 7) {
        std::cerr << "Usage: " << argv[0] << " <weights.txt> <input_dir> <image_count> <output_dir> [input_filename] [repetitions]\n";
        return 1;
    }

    try {
        const fs::path weights_path = argv[1];
        const fs::path input_dir = argv[2];
        const uint32_t image_count = static_cast<uint32_t>(std::stoul(argv[3]));
        const fs::path output_dir = argv[4];
        const std::string input_filename = argc > 5 ? argv[5] : "primary_squash_output.txt";
        const uint32_t repetitions = argc > 6 ? static_cast<uint32_t>(std::stoul(argv[6])) : 100;

        if (image_count == 0 || repetitions == 0) {
            throw std::runtime_error("image_count and repetitions must be greater than zero");
        }

        auto weights = load_values(weights_path, WEIGHT_SIZE);
        std::vector<float> inputs(static_cast<std::size_t>(image_count) * INPUT_SIZE);

        for (uint32_t i = 0; i < image_count; ++i) {
            const auto values = load_values(input_path(input_dir, i, input_filename), INPUT_SIZE);
            std::copy(values.begin(), values.end(), inputs.begin() + static_cast<std::size_t>(i) * INPUT_SIZE);
        }

        std::vector<float> output(OUTPUT_SIZE);

        for (uint32_t i = 0; i < WARMUP_RUNS; ++i) {
            float* input = inputs.data() + static_cast<std::size_t>(i % image_count) * INPUT_SIZE;
            dynamic_routing(input, weights.data(), output.data());
        }

        const uint64_t runs = static_cast<uint64_t>(image_count) * repetitions;

        std::cout << "MEASUREMENT_START" << std::endl;

        const auto start = Clock::now();

        for (uint32_t repeat = 0; repeat < repetitions; ++repeat) {
            for (uint32_t i = 0; i < image_count; ++i) {
                float* input = inputs.data() + static_cast<std::size_t>(i) * INPUT_SIZE;
                dynamic_routing(input, weights.data(), output.data());
            }
        }

        const auto end = Clock::now();

        std::cout << "MEASUREMENT_END" << std::endl;

        const double total_software_ms = std::chrono::duration<double, std::milli>(end - start).count();
        const double latency_per_inference_ms = total_software_ms / static_cast<double>(runs);

        std::cout << std::fixed << std::setprecision(6);
        std::cout << "RUNS=" << runs << '\n';
        std::cout << "SOFTWARE_ACTIVE_WINDOW_MS=" << total_software_ms << '\n';
        std::cout << "SOFTWARE_LATENCY_PER_INFERENCE_MS=" << latency_per_inference_ms << '\n';

        fs::create_directories(output_dir);

        for (uint32_t i = 0; i < image_count; ++i) {
            float* input = inputs.data() + static_cast<std::size_t>(i) * INPUT_SIZE;
            dynamic_routing(input, weights.data(), output.data());
            dump_output(output_dir / ("img" + std::to_string(i) + ".txt"), output.data());
        }

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}