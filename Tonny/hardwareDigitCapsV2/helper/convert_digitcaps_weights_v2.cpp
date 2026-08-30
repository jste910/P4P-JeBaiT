#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

constexpr std::size_t DIGITCAPS_WEIGHT_COUNT = 1474560;

// Q16.16 scale used by DigitCaps input and output. It is not used to
// quantize the INT8 weights.
static constexpr float FIXED_SCALE = 65536.0f;

// Symmetric per-tensor scale used by the v2 HLS DigitCaps kernel.
static constexpr float DIGITCAPS_WEIGHT_SCALE =
    0.004576775032704271f;

static int8_t float_to_int8_weight(float x)
{
    int q = static_cast<int>(
        std::llround(x / DIGITCAPS_WEIGHT_SCALE));

    if (q > 127)
        q = 127;

    if (q < -127)
        q = -127;

    return static_cast<int8_t>(q);
}

static void convert_float_to_int8_weights(
    const float* input,
    int8_t* output,
    std::size_t size)
{
    for (std::size_t i = 0; i < size; ++i)
        output[i] = float_to_int8_weight(input[i]);
}

int main(int argc, char* argv[])
{
    if (argc != 3) {
        std::cerr
            << "Usage: " << argv[0]
            << " <float_weights.txt> <int8_weights.bin>\n";
        return 1;
    }

    try {
        std::ifstream input_file(argv[1]);

        if (!input_file)
            throw std::runtime_error(
                "Cannot open float weight file: " +
                std::string(argv[1]));

        std::vector<float> float_weights(
            DIGITCAPS_WEIGHT_COUNT);

        for (std::size_t i = 0;
             i < DIGITCAPS_WEIGHT_COUNT;
             ++i)
        {
            if (!(input_file >> float_weights[i])) {
                throw std::runtime_error(
                    "Insufficient weights at index " +
                    std::to_string(i));
            }
        }

        float extra_weight;
        if (input_file >> extra_weight) {
            throw std::runtime_error(
                "Input contains more than " +
                std::to_string(DIGITCAPS_WEIGHT_COUNT) +
                " weights");
        }

        std::vector<int8_t> int8_weights(
            DIGITCAPS_WEIGHT_COUNT);

        convert_float_to_int8_weights(
            float_weights.data(),
            int8_weights.data(),
            int8_weights.size());

        std::ofstream output_file(
            argv[2],
            std::ios::binary);

        if (!output_file)
            throw std::runtime_error(
                "Cannot create INT8 weight file: " +
                std::string(argv[2]));

        output_file.write(
            reinterpret_cast<const char*>(
                int8_weights.data()),
            static_cast<std::streamsize>(
                int8_weights.size() * sizeof(int8_t)));

        if (!output_file)
            throw std::runtime_error(
                "Failed to write INT8 weights");

        std::cout
            << "WEIGHTS=" << int8_weights.size() << '\n'
            << "BYTES="
            << int8_weights.size() * sizeof(int8_t) << '\n'
            << "WEIGHT_SCALE="
            << DIGITCAPS_WEIGHT_SCALE << '\n'
            << "FIXED_SCALE=" << FIXED_SCALE << '\n';

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
