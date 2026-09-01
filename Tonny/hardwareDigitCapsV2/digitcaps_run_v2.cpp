#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "Accel_Wrapper2.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t inputSize = wrapper_constants_v2::DIGITCAPS_INPUT_COUNT;
constexpr std::size_t weightCount = wrapper_constants_v2::DIGITCAPS_WEIGHT_COUNT;
constexpr std::size_t weightBytes = wrapper_constants_v2::DIGITCAPS_WEIGHT_BYTES;
constexpr std::size_t outputSize = wrapper_constants_v2::DIGITCAPS_OUTPUT_COUNT;

fs::path imagePath(const fs::path& dir, uint64_t index)
{
    return dir / ("img" + std::to_string(index) + ".txt");
}

std::vector<int8_t> loadWeights(const fs::path& path)
{
    std::ifstream file(path, std::ios::binary);
    if (!file)
        throw std::runtime_error("Cannot open weights: " + path.string());

    std::vector<int8_t> data(weightCount);
    file.read(reinterpret_cast<char*>(data.data()), weightBytes);

    if (file.gcount() != static_cast<std::streamsize>(weightBytes))
        throw std::runtime_error("Incorrect weight file size");

    return data;
}

std::vector<float> loadInput(const fs::path& path)
{
    std::ifstream file(path);
    if (!file)
        throw std::runtime_error("Cannot open input: " + path.string());

    std::vector<float> data(inputSize);
    for (float& value : data)
        if (!(file >> value))
            throw std::runtime_error("Invalid input: " + path.string());

    return data;
}

void saveOutput(const fs::path& path, const std::vector<float>& data)
{
    std::ofstream file(path);
    if (!file)
        throw std::runtime_error("Cannot write output: " + path.string());

    file << std::fixed << std::setprecision(10);
    for (float value : data)
        file << value << '\n';
}

int main(int argc, char* argv[])
{
    try {
        if (argc != 6) {
            std::cerr << "Usage: " << argv[0]
                      << " <xclbin> <weights.bin> <input_dir>"
                      << " <image_count> <output_dir>\n";
            return 1;
        }

        const std::string xclbinPath = argv[1];
        const fs::path inputDir = argv[3];
        const uint64_t imageCount = std::stoull(argv[4]);
        const fs::path outputDir = argv[5];

        if (imageCount == 0)
            throw std::invalid_argument("image_count must be greater than zero");

        fs::create_directories(outputDir);

        const auto weights = loadWeights(argv[2]);
        std::vector<float> output(outputSize);

        Accel_Wrapper2 accelerator(xclbinPath);
        accelerator.initialise_digitcaps_kernel_fixed(weights.data());

        double totalMs = 0.0;

        for (uint64_t i = 0; i < imageCount; ++i) {
            const auto input = loadInput(imagePath(inputDir, i));
            accelerator.update_digitcaps_kernel(input.data());

            std::cout << "IMAGE_INDEX=" << i
                      << "\nMEASUREMENT_START" << std::endl;

            const auto start = Clock::now();
            accelerator.run_digitcaps_kernel();
            const auto end = Clock::now();

            std::cout << "MEASUREMENT_END" << std::endl;

            const double latencyMs =
                std::chrono::duration<double, std::milli>(end - start).count();

            totalMs += latencyMs;

            std::cout << std::fixed << std::setprecision(6)
                      << "IMAGE_LATENCY_MS=" << latencyMs << '\n';

            accelerator.read_digitcaps_kernel(output.data());
            saveOutput(imagePath(outputDir, i), output);
        }

        std::cout << std::fixed << std::setprecision(6)
                  << "IMAGES=" << imageCount << '\n'
                  << "TOTAL_LATENCY_MS=" << totalMs << '\n'
                  << "AVERAGE_LATENCY_PER_IMAGE_MS="
                  << totalMs / static_cast<double>(imageCount) << '\n';

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}