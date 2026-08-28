#include <algorithm>
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

fs::path input_path(
    const fs::path& dir,
    uint32_t index,
    const std::string& filename)
{
    const std::string name =
        "img" + std::to_string(index);

    const fs::path nested =
        dir / name / filename;

    const fs::path flat =
        dir / (name + ".txt");

    if (fs::exists(nested))
        return nested;

    if (fs::exists(flat))
        return flat;

    throw std::runtime_error(
        "Cannot find input for " + name);
}

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
    if (argc < 5 || argc > 7) {
        std::cerr
            << "Usage: " << argv[0]
            << " <xclbin> <weights.txt> <input_dir> <image_count>"
            << " [input_filename] [repetitions]\n";
        return 1;
    }

    try {
        const std::string xclbin_path = argv[1];
        const fs::path weights_path = argv[2];
        const fs::path input_dir = argv[3];

        const uint32_t image_count =
            static_cast<uint32_t>(std::stoul(argv[4]));

        const std::string input_filename =
            argc > 5
                ? argv[5]
                : "primary_squash_output.txt";

        const uint32_t repetitions =
            argc > 6
                ? static_cast<uint32_t>(std::stoul(argv[6]))
                : 100;

        if (image_count == 0 || repetitions == 0)
            throw std::runtime_error(
                "image_count and repetitions must be greater than zero");

        // All setup is outside the update measurement window.
        const auto weights =
            load_values(weights_path, WEIGHT_SIZE);

        std::vector<float> inputs(
            static_cast<std::size_t>(image_count)
            * INPUT_SIZE);

        for (uint32_t i = 0; i < image_count; ++i) {
            const auto values =
                load_values(
                    input_path(input_dir, i, input_filename),
                    INPUT_SIZE);

            std::copy(
                values.begin(),
                values.end(),
                inputs.begin()
                    + static_cast<std::size_t>(i)
                      * INPUT_SIZE);
        }

        Accel_Wrapper3 accelerator(xclbin_path);

        accelerator.initialise_digitcaps_kernel(
            weights.data());

        const uint64_t calls =
            static_cast<uint64_t>(image_count)
            * repetitions;

        std::cout
            << "PHASE=DIGITCAPS_UPDATE\n"
            << "MEASUREMENT_START"
            << std::endl;

        const auto start = Clock::now();

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

                accelerator.update_digitcaps_kernel(
                    input);
            }
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
            << "CALLS=" << calls << '\n'
            << "UPDATE_TOTAL_MS=" << elapsed_ms << '\n'
            << "UPDATE_LATENCY_PER_CALL_MS="
            << elapsed_ms / static_cast<double>(calls)
            << '\n';

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
