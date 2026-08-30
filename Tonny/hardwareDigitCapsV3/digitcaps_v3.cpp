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

constexpr std::size_t inputSize = wrapper_constants_v3::DIGITCAPS_INPUT_COUNT;
constexpr std::size_t weightCount = wrapper_constants_v3::DIGITCAPS_WEIGHT_COUNT;
constexpr std::size_t weightBytes = wrapper_constants_v3::DIGITCAPS_WEIGHT_BYTES;
constexpr std::size_t outputSize = wrapper_constants_v3::DIGITCAPS_OUTPUT_COUNT;
constexpr uint32_t warmupRuns = 10;

fs::path getInputPath(const fs::path& dir, uint32_t index, const std::string& fileName)
{
    const std::string imageName = "img" + std::to_string(index);
    const fs::path nestedPath = dir / imageName / fileName;
    return fs::exists(nestedPath) ? nestedPath : dir / (imageName + ".txt");
}

std::vector<int8_t> loadWeights(const fs::path& path)
{
    std::vector<int8_t> weights(weightCount);
    std::ifstream file(path, std::ios::binary);
    file.read(reinterpret_cast<char*>(weights.data()), weightBytes);
    return weights;
}

std::vector<float> loadValues(const fs::path& path, std::size_t count)
{
    std::vector<float> values(count);
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
    const fs::path weightsPath = argv[2];
    const fs::path inputDir = argv[3];
    const uint32_t imageCount = std::stoul(argv[4]);
    const fs::path outputDir = argv[5];
    const std::string inputFileName = argc > 6 ? argv[6] : "primary_squash_output.txt";
    const uint32_t repetitions = argc > 7 ? std::stoul(argv[7]) : 100;

    const auto weights = loadWeights(weightsPath);
    std::vector<float> inputs(static_cast<std::size_t>(imageCount) * inputSize);

    for (uint32_t i = 0; i < imageCount; ++i) {
        const auto values = loadValues(getInputPath(inputDir, i, inputFileName), inputSize);
        std::copy(values.begin(), values.end(), inputs.begin() + static_cast<std::size_t>(i) * inputSize);
    }

    Accel_Wrapper3 accelerator(xclbinPath);
    accelerator.initialise_digitcaps_kernel_fixed(weights.data());

    std::vector<float> output(outputSize);
    for (uint32_t i = 0; i < warmupRuns; ++i) {
        accelerator.update_digitcaps_kernel(inputs.data());
        accelerator.run_digitcaps_kernel();
        accelerator.read_digitcaps_kernel(output.data());
    }

    std::vector<float> savedOutput(static_cast<std::size_t>(imageCount) * outputSize);
    double totalKernelMs = 0.0;

    std::cout << "MEASUREMENT_START" << std::endl;

    for (uint32_t repeat = 0; repeat < repetitions; ++repeat) {
        for (uint32_t i = 0; i < imageCount; ++i) {
            const float* input = inputs.data() + static_cast<std::size_t>(i) * inputSize;
            accelerator.update_digitcaps_kernel(input);

            const auto start = Clock::now();
            accelerator.run_digitcaps_kernel();
            const auto end = Clock::now();

            totalKernelMs += std::chrono::duration<double, std::milli>(end - start).count();
            accelerator.read_digitcaps_kernel(output.data());

            if (repeat + 1 == repetitions)
                std::copy(output.begin(), output.end(), savedOutput.begin() + static_cast<std::size_t>(i) * outputSize);
        }
    }

    std::cout << "MEASUREMENT_END" << std::endl;

    const uint64_t runs = static_cast<uint64_t>(imageCount) * repetitions;
    std::cout << std::fixed << std::setprecision(6)
              << "RUNS=" << runs << '\n'
              << "KERNEL_ACTIVE_WINDOW_MS=" << totalKernelMs << '\n'
              << "KERNEL_LATENCY_PER_INFERENCE_MS=" << totalKernelMs / runs << '\n';

    fs::create_directories(outputDir);
    for (uint32_t i = 0; i < imageCount; ++i)
        dumpOutput(outputDir / ("img" + std::to_string(i) + ".txt"),
                   savedOutput.data() + static_cast<std::size_t>(i) * outputSize);

    return 0;
}
