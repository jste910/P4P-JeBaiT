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

constexpr std::size_t WEIGHT_SIZE =
    wrapper_constants_v3::DIGITCAPS_WEIGHT_COUNT;

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

int main(int argc, char* argv[])
{
    if (argc < 3 || argc > 4) {
        std::cerr
            << "Usage: " << argv[0]
            << " <xclbin> <weights.txt> [repetitions]\n";
        return 1;
    }

    try {
        const std::string xclbin_path = argv[1];
        const fs::path weights_path = argv[2];

        const uint64_t repetitions =
            argc > 3
                ? std::stoull(argv[3])
                : 100;

        if (repetitions == 0)
            throw std::runtime_error(
                "repetitions must be greater than zero");

        // File loading and wrapper construction are outside the window.
        const auto weights =
            load_values(weights_path, WEIGHT_SIZE);

        Accel_Wrapper3 accelerator(xclbin_path);

        std::cout
            << "PHASE=DIGITCAPS_INIT\n"
            << "MEASUREMENT_START"
            << std::endl;

        const auto start = Clock::now();

        for (uint64_t i = 0; i < repetitions; ++i) {
            accelerator.initialise_digitcaps_kernel(
                weights.data());
        }

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
            << "INITIALISE_TOTAL_MS=" << elapsed_ms << '\n'
            << "INITIALISE_LATENCY_PER_CALL_MS="
            << elapsed_ms / static_cast<double>(repetitions)
            << '\n';

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
