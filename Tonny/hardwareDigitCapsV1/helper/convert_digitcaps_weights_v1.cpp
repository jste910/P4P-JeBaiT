#include <cmath>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

constexpr std::size_t WEIGHT_COUNT = 1474560;
constexpr double FIXED_SCALE = 65536.0;

static int32_t float_to_fixed32_16(float value)
{
    const double scaled =
        std::round(static_cast<double>(value) * FIXED_SCALE);

    if (scaled >
        static_cast<double>(std::numeric_limits<int32_t>::max()))
    {
        return std::numeric_limits<int32_t>::max();
    }

    if (scaled <
        static_cast<double>(std::numeric_limits<int32_t>::min()))
    {
        return std::numeric_limits<int32_t>::min();
    }

    return static_cast<int32_t>(scaled);
}

int main(int argc, char* argv[])
{
    if (argc != 3) {
        std::cerr
            << "Usage: " << argv[0]
            << " <float_weights.txt> <fixed32_16_weights.bin>\n";
        return 1;
    }

    try {
        std::ifstream input(argv[1]);

        if (!input) {
            throw std::runtime_error(
                "Cannot open float weight file: " +
                std::string(argv[1]));
        }

        std::vector<int32_t> fixedWeights(WEIGHT_COUNT);

        for (std::size_t i = 0; i < WEIGHT_COUNT; ++i) {
            float value;

            if (!(input >> value)) {
                throw std::runtime_error(
                    "Insufficient weights at index " +
                    std::to_string(i));
            }

            fixedWeights[i] =
                float_to_fixed32_16(value);
        }

        float extraValue;

        if (input >> extraValue) {
            throw std::runtime_error(
                "Weight file contains more than " +
                std::to_string(WEIGHT_COUNT) +
                " values");
        }

        std::ofstream output(
            argv[2],
            std::ios::binary);

        if (!output) {
            throw std::runtime_error(
                "Cannot create output file: " +
                std::string(argv[2]));
        }

        const std::size_t outputBytes =
            fixedWeights.size() * sizeof(int32_t);

        output.write(
            reinterpret_cast<const char*>(
                fixedWeights.data()),
            static_cast<std::streamsize>(outputBytes));

        if (!output) {
            throw std::runtime_error(
                "Failed to write fixed-point weights");
        }

        std::cout
            << "WEIGHTS=" << fixedWeights.size() << '\n'
            << "BYTES=" << outputBytes << '\n'
            << "FORMAT=Q16.16_INT32\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "ERROR: " << error.what() << '\n';
        return 1;
    }
}