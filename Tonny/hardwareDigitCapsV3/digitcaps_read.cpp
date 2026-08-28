#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
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

std::vector<float> load_values(
    const fs::path& path,
    std::size_t count)
{
    std::ifstream file(path);

    if (!file)
        throw std::runtime_error(
            "Cannot open file: " + path.string());

    std::vector<float> values(count);

    for (std::size_t i = 0; i < count; ++i) {
        if (!(file >> values[i]))
            throw std::runtime_error(
                "Expected " + std::to_string(count)
                + " values in: " + path.string());
    }

    return values;
}

void dump_output(
    const fs::path& path,
    const float* data)
{
    std::ofstream file(path);

    if (!file)
        throw std::runtime_error(
            "Cannot create file: " + path.string());

    file << std::fixed
         << std::setprecision(10);

    for (std::size_t i = 0; i < OUTPUT_SIZE; ++i)
        file << data[i] << '\n';
}

int main(int argc, char* argv[])
{
    if (argc < 4 || argc > 6) {
        std::cerr
            << "Usage: " << argv[0]
            << " <xclbin> <weights.txt> <input.txt>"
            << " [repetitions] [output.txt]\n";
        return 1;
    }

    try {
        const std::string xclbin_path = argv[1];
        const fs::path weights_path = argv[2];
        const fs::path input_path = argv[3];

        const uint64_t repetitions =
            argc > 4
                ? std::stoull(argv[4])
                : 100;

        if (repetitions == 0)
            throw std::runtime_error(
                "repetitions must be greater than zero");

        const auto weights =
            load_values(weights_path, WEIGHT_SIZE);

        const auto input =
            load_values(input_path, INPUT_SIZE);

        std::vector<float> output(OUTPUT_SIZE);

        Accel_Wrapper3 accelerator(xclbin_path);

        // Produce one valid result before measuring read().
        accelerator.initialise_digitcaps_kernel(
            weights.data());

        accelerator.update_digitcaps_kernel(
            input.data());

        accelerator.run_digitcaps_kernel();

        std::cout
            << "PHASE=DIGITCAPS_READ\n"
            << "MEASUREMENT_START"
            << std::endl;

        const auto start = Clock::now();

        for (uint64_t i = 0; i < repetitions; ++i)
            accelerator.read_digitcaps_kernel(
                output.data());

        const auto end = Clock::now();

        std::cout
            << "MEASUREMENT_END"
            << std::endl;

        const double elapsed_ms =
            std::chrono::duration<double, std::milli>(
                end - start)
                .count();

        std::cout
            << std::fixed
            << std::setprecision(6)
            << "CALLS=" << repetitions << '\n'
            << "READ_TOTAL_MS=" << elapsed_ms << '\n'
            << "READ_LATENCY_PER_CALL_MS="
            << elapsed_ms / static_cast<double>(repetitions)
            << '\n';

        // Optional file writing remains outside the read window.
        if (argc > 5)
            dump_output(argv[5], output.data());

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
