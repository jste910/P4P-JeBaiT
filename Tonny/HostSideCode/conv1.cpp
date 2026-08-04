#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "common.h"
#include "vart/runner_ext.hpp"
#include "xir/graph/graph.hpp"
#include "xir/tensor/tensor.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

constexpr int INPUT_SIZE = 28 * 28;
constexpr int OUTPUT_SIZE = 20 * 20 * 256;
constexpr uint32_t WARMUP_RUNS = 10;

std::vector<float> load_images(const std::string& path, uint32_t count)
{
    std::ifstream file(path, std::ios::binary);
    unsigned char header[16];
    file.read(reinterpret_cast<char*>(header), 16);

    std::vector<float> images(static_cast<size_t>(count) * INPUT_SIZE);
    std::vector<uint8_t> raw(INPUT_SIZE);

    for (uint32_t i = 0; i < count; ++i) {
        file.read(reinterpret_cast<char*>(raw.data()), INPUT_SIZE);

        for (int j = 0; j < INPUT_SIZE; ++j)
            images[static_cast<size_t>(i) * INPUT_SIZE + j] =
                raw[j] / 255.0f;
    }

    return images;
}

void dump_output(const fs::path& path, const float* data)
{
    std::ofstream file(path);
    file << std::setprecision(10);

    for (int i = 0; i < OUTPUT_SIZE; ++i)
        file << data[i] << '\n';
}

void run_conv1(
    vart::RunnerExt* runner,
    const std::vector<float>& images,
    uint32_t image_count,
    uint32_t repetitions,
    const fs::path& output_dir)
{
    const auto* input_tensor = runner->get_input_tensors()[0];
    const auto* output_tensor = runner->get_output_tensors()[0];

    const auto input_shape = input_tensor->get_shape();
    const auto output_shape = output_tensor->get_shape();
    const uint32_t batch_size = static_cast<uint32_t>(input_shape[0]);

    std::vector<float> input(
        static_cast<size_t>(batch_size) * INPUT_SIZE);

    std::vector<float> output(
        static_cast<size_t>(batch_size) * OUTPUT_SIZE);

    std::vector<float> saved_output(
        static_cast<size_t>(image_count) * OUTPUT_SIZE);

    auto input_wrapper =
        std::shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                input_tensor->get_name(),
                input_shape,
                {xir::DataType::FLOAT, 32U}));

    auto output_wrapper =
        std::shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                output_tensor->get_name(),
                output_shape,
                {xir::DataType::FLOAT, 32U}));

    auto input_buffer =
        std::make_unique<CpuFlatTensorBuffer>(
            input.data(),
            input_wrapper.get());

    auto output_buffer =
        std::make_unique<CpuFlatTensorBuffer>(
            output.data(),
            output_wrapper.get());

    std::vector<vart::TensorBuffer*> inputs{input_buffer.get()};
    std::vector<vart::TensorBuffer*> outputs{output_buffer.get()};

    auto execute_batch = [&](uint32_t base, bool save) {
        const uint32_t run_size =
            std::min(batch_size, image_count - base);

        std::fill(input.begin(), input.end(), 0.0f);

        std::copy_n(
            images.data() + static_cast<size_t>(base) * INPUT_SIZE,
            static_cast<size_t>(run_size) * INPUT_SIZE,
            input.data());

        const auto job = runner->execute_async(inputs, outputs);
        runner->wait(job.first, -1);

        if (save)
            std::copy_n(
                output.data(),
                static_cast<size_t>(run_size) * OUTPUT_SIZE,
                saved_output.data() +
                    static_cast<size_t>(base) * OUTPUT_SIZE);
    };

    for (uint32_t i = 0; i < WARMUP_RUNS; ++i)
        execute_batch(0, false);

    std::cout << "MEASUREMENT_START" << std::endl;
    const auto start = Clock::now();

    for (uint32_t repeat = 0; repeat < repetitions; ++repeat)
        for (uint32_t base = 0;
             base < image_count;
             base += batch_size)
            execute_batch(base, repeat + 1 == repetitions);

    const auto end = Clock::now();
    std::cout << "MEASUREMENT_END" << std::endl;

    const uint64_t runs =
        static_cast<uint64_t>(image_count) * repetitions;

    const double total_ms =
        std::chrono::duration<double, std::milli>(end - start).count();

    std::cout << std::fixed << std::setprecision(6)
              << "RUNS=" << runs << '\n'
              << "ACTIVE_WINDOW_MS=" << total_ms << '\n'
              << "LATENCY_PER_INFERENCE_MS="
              << total_ms / runs << '\n';

    fs::create_directories(output_dir);

    for (uint32_t i = 0; i < image_count; ++i) {
        const fs::path dir =
            output_dir / ("img" + std::to_string(i));

        fs::create_directories(dir);

        dump_output(
            dir / "convolutional_output.txt",
            saved_output.data() +
                static_cast<size_t>(i) * OUTPUT_SIZE);
    }
}

int main(int argc, char* argv[])
{
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

    const auto images =
        load_images(image_path, image_count);

    auto graph =
        xir::Graph::deserialize(model_path);

    auto subgraphs =
        get_dpu_subgraph(graph.get());

    auto attrs =
        xir::Attrs::create();

    auto runner =
        vart::RunnerExt::create_runner(
            subgraphs[0],
            attrs.get());

    run_conv1(
        runner.get(),
        images,
        image_count,
        repetitions,
        output_dir);

    return 0;
}