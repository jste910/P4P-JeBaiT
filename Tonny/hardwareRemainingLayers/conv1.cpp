#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "common.h"
#include "vart/runner_ext.hpp"
#include "xir/graph/graph.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr std::size_t IMAGE_SIZE = 28 * 28;
constexpr uint32_t WARMUP_RUNS = 10;

static int8_t quantise(float value, int fix_point)
{
    const int result = static_cast<int>(
        std::lround(value * std::ldexp(1.0f, fix_point)));

    return static_cast<int8_t>(
        std::clamp(result, -128, 127));
}

static std::vector<int8_t> load_images(
    const std::string& path,
    uint32_t count,
    int input_fix_point)
{
    std::ifstream file(path, std::ios::binary);
    if (!file)
        throw std::runtime_error("Cannot open image file: " + path);

    unsigned char header[16];
    file.read(reinterpret_cast<char*>(header), sizeof(header));

    if (!file)
        throw std::runtime_error("Invalid MNIST image header");

    std::vector<int8_t> images(
        static_cast<std::size_t>(count) * IMAGE_SIZE);

    std::vector<uint8_t> raw(IMAGE_SIZE);

    for (uint32_t i = 0; i < count; ++i) {
        file.read(
            reinterpret_cast<char*>(raw.data()),
            static_cast<std::streamsize>(raw.size()));

        if (!file)
            throw std::runtime_error(
                "Unexpected end of MNIST image file");

        for (std::size_t j = 0; j < IMAGE_SIZE; ++j) {
            images[static_cast<std::size_t>(i) * IMAGE_SIZE + j] =
                quantise(
                    static_cast<float>(raw[j]) / 255.0f,
                    input_fix_point);
        }
    }

    return images;
}

static void dump_output(
    const fs::path& path,
    const int8_t* output,
    std::size_t output_size,
    int output_fix_point)
{
    std::ofstream file(path);
    if (!file)
        throw std::runtime_error(
            "Cannot create output file: " + path.string());

    const float scale = std::ldexp(1.0f, -output_fix_point);

    file << std::setprecision(10);

    for (std::size_t i = 0; i < output_size; ++i)
        file << static_cast<float>(output[i]) * scale << '\n';
}

int main(int argc, char* argv[])
{
    if (argc < 4 || argc > 6) {
        std::cerr
            << "Usage: " << argv[0]
            << " <xmodel> <mnist_images> <image_count> "
               "[output_dir] [repetitions]\n";
        return 1;
    }

    try {
        const std::string model_path = argv[1];
        const std::string image_path = argv[2];
        const uint32_t image_count =
            static_cast<uint32_t>(std::stoul(argv[3]));
        const fs::path output_dir =
            argc > 4 ? argv[4] : "dump_capsnet_hw";
        const uint32_t repetitions =
            argc > 5
                ? static_cast<uint32_t>(std::stoul(argv[5]))
                : 100;

        if (image_count == 0 || repetitions == 0)
            throw std::runtime_error(
                "image_count and repetitions must be non-zero");

        auto graph = xir::Graph::deserialize(model_path);
        auto subgraphs = get_dpu_subgraph(graph.get());

        if (subgraphs.empty())
            throw std::runtime_error("No DPU subgraph found");

        auto attrs = xir::Attrs::create();
        auto runner = vart::RunnerExt::create_runner(
            subgraphs[0], attrs.get());

        const auto* input_tensor =
            runner->get_input_tensors()[0];
        const auto* output_tensor =
            runner->get_output_tensors()[0];

        if (input_tensor->get_data_type().bit_width != 8 ||
            output_tensor->get_data_type().bit_width != 8)
            throw std::runtime_error(
                "Expected native INT8 DPU tensors");

        const std::size_t batch_size =
            input_tensor->get_shape()[0];

        const std::size_t input_size =
            input_tensor->get_element_num() / batch_size;

        const std::size_t output_size =
            output_tensor->get_element_num() / batch_size;

        if (input_size != IMAGE_SIZE)
            throw std::runtime_error(
                "Unexpected Conv1 input size: " +
                std::to_string(input_size));

        const int input_fix_point =
            input_tensor->get_attr<int>("fix_point");

        const int output_fix_point =
            output_tensor->get_attr<int>("fix_point");

        // Quantised once, before measurement.
        const auto images = load_images(
            image_path, image_count, input_fix_point);

        std::vector<int8_t> input(batch_size * input_size);
        std::vector<int8_t> output(batch_size * output_size);
        std::vector<int8_t> saved(
            static_cast<std::size_t>(image_count) * output_size);

        auto input_buffer =
            std::make_unique<CpuFlatTensorBuffer>(
                input.data(), input_tensor);

        auto output_buffer =
            std::make_unique<CpuFlatTensorBuffer>(
                output.data(), output_tensor);

        std::vector<vart::TensorBuffer*> inputs{
            input_buffer.get()
        };

        std::vector<vart::TensorBuffer*> outputs{
            output_buffer.get()
        };

        auto prepare_batch = [&](uint32_t base) {
            const std::size_t run_size = std::min<std::size_t>(
                batch_size, image_count - base);

            std::fill(input.begin(), input.end(), 0);

            std::copy_n(
                images.data() +
                    static_cast<std::size_t>(base) * input_size,
                run_size * input_size,
                input.data());

            return run_size;
        };

        prepare_batch(0);

        for (uint32_t i = 0; i < WARMUP_RUNS; ++i) {
            const auto job =
                runner->execute_async(inputs, outputs);
            runner->wait(job.first, -1);
        }

        double total_dpu_ms = 0.0;
        uint64_t total_batches = 0;
        uint64_t total_images = 0;

        std::cout << "MEASUREMENT_START" << std::endl;

        for (uint32_t repeat = 0;
             repeat < repetitions;
             ++repeat) {
            for (uint32_t base = 0;
                 base < image_count;
                 base += batch_size) {
                const std::size_t run_size =
                    prepare_batch(base);

                const auto start = Clock::now();

                const auto job =
                    runner->execute_async(inputs, outputs);

                runner->wait(job.first, -1);

                const auto end = Clock::now();

                total_dpu_ms +=
                    std::chrono::duration<double, std::milli>(
                        end - start).count();

                ++total_batches;
                total_images += run_size;

                if (repeat + 1 == repetitions) {
                    std::copy_n(
                        output.data(),
                        run_size * output_size,
                        saved.data() +
                            static_cast<std::size_t>(base) *
                                output_size);
                }
            }
        }

        std::cout << "MEASUREMENT_END\n"
                  << std::fixed
                  << std::setprecision(6)
                  << "RUNS=" << total_images << '\n'
                  << "BATCH_SIZE=" << batch_size << '\n'
                  << "BATCHES=" << total_batches << '\n'
                  << "INPUT_FIX_POINT="
                  << input_fix_point << '\n'
                  << "OUTPUT_FIX_POINT="
                  << output_fix_point << '\n'
                  << "DPU_ACTIVE_WINDOW_MS="
                  << total_dpu_ms << '\n'
                  << "DPU_LATENCY_PER_BATCH_MS="
                  << total_dpu_ms / total_batches << '\n'
                  << "DPU_LATENCY_PER_INFERENCE_MS="
                  << total_dpu_ms / total_images << '\n';

        // Dequantisation and file output are outside measurement.
        for (uint32_t i = 0; i < image_count; ++i) {
            const fs::path directory =
                output_dir / ("img" + std::to_string(i));

            fs::create_directories(directory);

            dump_output(
                directory / "convolutional_output.txt",
                saved.data() +
                    static_cast<std::size_t>(i) * output_size,
                output_size,
                output_fix_point);
        }

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}