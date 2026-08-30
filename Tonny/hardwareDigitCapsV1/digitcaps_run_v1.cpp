#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "Accel_Wrapper1.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t inputSize = wrapper_constants_v1::DIGITCAPS_INPUT_COUNT;
constexpr std::size_t weightCount = wrapper_constants_v1::DIGITCAPS_WEIGHT_COUNT;
constexpr std::size_t weightBytes = wrapper_constants_v1::DIGITCAPS_WEIGHT_BYTES;
constexpr std::size_t outputSize = wrapper_constants_v1::DIGITCAPS_OUTPUT_COUNT;

std::vector<int32_t> loadWeights(const fs::path& path)
{
    std::vector<int32_t> weights(weightCount);
    std::ifstream file(path, std::ios::binary);
    file.read(reinterpret_cast<char*>(weights.data()), weightBytes);
    return weights;
}

std::vector<float> loadValues(const fs::path& path)
{
    std::vector<float> values(inputSize);
    std::ifstream file(path);

    for (float& value : values)
        file >> value;

    return values;
}

void dumpOutput(const fs::path& path, const float* data)
{
    std::ofstream file(path);
    file << std::fixed << std::setprecision(10);

    for (std::size_t i = 0; i < outputSize; ++i)
        file << data[i] << '\n';
}

int main(int argc, char* argv[])
{
    const std::string xclbinPath = argv[1];
    const auto weights = loadWeights(argv[2]);
    const auto input = loadValues(argv[3]);
    const uint64_t repetitions =
        argc > 4 ? std::stoull(argv[4]) : 100;

    Accel_Wrapper1 accelerator(xclbinPath);
    accelerator.initialise_digitcaps_kernel_fixed(weights.data());
    accelerator.update_digitcaps_kernel(input.data());

    std::cout << "PHASE=DIGITCAPS_RUN\nMEASUREMENT_START" << std::endl;
    const auto start = Clock::now();

    for (uint64_t i = 0; i < repetitions; ++i)
        accelerator.run_digitcaps_kernel();

    const auto end = Clock::now();
    std::cout << "MEASUREMENT_END" << std::endl;

    const double elapsedMs =
        std::chrono::duration<double, std::milli>(
            end - start).count();

    std::cout << std::fixed << std::setprecision(6)
              << "CALLS=" << repetitions << '\n'
              << "RUN_TOTAL_MS=" << elapsedMs << '\n'
              << "RUN_LATENCY_PER_CALL_MS="
              << elapsedMs / repetitions << '\n';

    if (argc > 5) {
        std::vector<float> output(outputSize);
        accelerator.read_digitcaps_kernel(output.data());
        dumpOutput(argv[5], output.data());
    }

    return 0;
}