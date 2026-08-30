#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#include "Accel_Wrapper2.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t inputSize = wrapper_constants::DIGITCAPS_INPUT_COUNT;
constexpr std::size_t weightCount = wrapper_constants::DIGITCAPS_WEIGHT_COUNT;
constexpr std::size_t weightBytes = wrapper_constants::DIGITCAPS_WEIGHT_BYTES;

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

std::vector<float> loadValues(const fs::path& path)
{
    std::vector<float> values(inputSize);
    std::ifstream file(path);
    for (float& value : values)
        file >> value;
    return values;
}

int main(int argc, char* argv[])
{
    const std::string xclbinPath = argv[1];
    const auto weights = loadWeights(argv[2]);
    const fs::path inputDir = argv[3];
    const uint32_t imageCount = std::stoul(argv[4]);
    const std::string inputFileName = argc > 5 ? argv[5] : "primary_squash_output.txt";
    const uint32_t repetitions = argc > 6 ? std::stoul(argv[6]) : 100;

    std::vector<float> inputs(static_cast<std::size_t>(imageCount) * inputSize);
    for (uint32_t i = 0; i < imageCount; ++i) {
        const auto values = loadValues(getInputPath(inputDir, i, inputFileName));
        std::copy(values.begin(), values.end(), inputs.begin() + static_cast<std::size_t>(i) * inputSize);
    }

    Accel_Wrapper2 accelerator(xclbinPath);
    accelerator.initialise_digitcaps_kernel_fixed(weights.data());

    const uint64_t calls = static_cast<uint64_t>(imageCount) * repetitions;
    std::cout << "PHASE=DIGITCAPS_UPDATE\nMEASUREMENT_START" << std::endl;
    const auto start = Clock::now();

    for (uint32_t repeat = 0; repeat < repetitions; ++repeat)
        for (uint32_t i = 0; i < imageCount; ++i)
            accelerator.update_digitcaps_kernel(
                inputs.data() + static_cast<std::size_t>(i) * inputSize);

    const auto end = Clock::now();
    std::cout << "MEASUREMENT_END" << std::endl;

    const double elapsedMs = std::chrono::duration<double, std::milli>(end - start).count();
    std::cout << std::fixed << std::setprecision(6)
              << "CALLS=" << calls << '\n'
              << "UPDATE_TOTAL_MS=" << elapsedMs << '\n'
              << "UPDATE_LATENCY_PER_CALL_MS=" << elapsedMs / calls << '\n';
}
