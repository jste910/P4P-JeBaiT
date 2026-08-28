#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

constexpr std::size_t WEIGHT_COUNT = 1474560;
constexpr float WEIGHT_SCALE = 64.0f;

static int8_t float_to_fixed7_1(float x)
{
    int32_t raw =
        static_cast<int32_t>(
            std::llround(x * WEIGHT_SCALE));

    if (raw > 63)
        raw = 63;

    if (raw < -64)
        raw = -64;

    return static_cast<int8_t>(raw);
}

int main(int argc, char* argv[])
{
    if (argc != 3) {
        std::cerr
            << "Usage: " << argv[0]
            << " <float_weights.txt> <fixed_weights.bin>\n";
        return 1;
    }

    try {
        std::ifstream input(argv[1]);

        if (!input)
            throw std::runtime_error(
                "Cannot open float weight file");

        std::vector<int8_t> fixed_weights(
            WEIGHT_COUNT);

        for (std::size_t i = 0;
             i < WEIGHT_COUNT;
             ++i)
        {
            float value;

            if (!(input >> value)) {
                throw std::runtime_error(
                    "Insufficient weights at index "
                    + std::to_string(i));
            }

            fixed_weights[i] =
                float_to_fixed7_1(value);
        }

        std::ofstream output(
            argv[2],
            std::ios::binary);

        if (!output)
            throw std::runtime_error(
                "Cannot create fixed weight file");

        output.write(
            reinterpret_cast<const char*>(
                fixed_weights.data()),
            static_cast<std::streamsize>(
                fixed_weights.size()));

        if (!output)
            throw std::runtime_error(
                "Failed to write fixed weights");

        std::cout
            << "WEIGHTS=" << WEIGHT_COUNT << '\n'
            << "BYTES=" << fixed_weights.size() << '\n';

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "ERROR: " << error.what() << '\n';
        return 1;
    }
}