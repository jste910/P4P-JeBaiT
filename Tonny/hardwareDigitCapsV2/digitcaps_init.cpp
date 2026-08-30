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

constexpr std::size_t weightCount = wrapper_constants::DIGITCAPS_WEIGHT_COUNT;
constexpr std::size_t weightBytes = wrapper_constants::DIGITCAPS_WEIGHT_BYTES;

std::vector<int8_t> loadWeights(const fs::path& path)
{
    std::vector<int8_t> weights(weightCount);
    std::ifstream file(path, std::ios::binary);
    file.read(reinterpret_cast<char*>(weights.data()), weightBytes);
    return weights;
}

int main(int argc, char* argv[])
{
    const std::string xclbinPath = argv[1];
    const auto weights = loadWeights(argv[2]);
    const uint64_t repetitions = argc > 3 ? std::stoull(argv[3]) : 100;
    Accel_Wrapper2 accelerator(xclbinPath);

    std::cout << "PHASE=DIGITCAPS_INIT\nMEASUREMENT_START" << std::endl;
    const auto start = Clock::now();

    for (uint64_t i = 0; i < repetitions; ++i)
        accelerator.initialise_digitcaps_kernel_fixed(weights.data());

    const auto end = Clock::now();
    std::cout << "MEASUREMENT_END" << std::endl;

    const double elapsedMs = std::chrono::duration<double, std::milli>(end - start).count();
    std::cout << std::fixed << std::setprecision(6)
              << "CALLS=" << repetitions << '\n'
              << "INITIALISE_TOTAL_MS=" << elapsedMs << '\n'
              << "INITIALISE_LATENCY_PER_CALL_MS=" << elapsedMs / repetitions << '\n';
}
