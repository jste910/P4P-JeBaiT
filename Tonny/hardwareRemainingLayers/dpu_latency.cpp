#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "common.h"
#include "vart/runner.hpp"
#include "vart/runner_ext.hpp"

using namespace std;
using Clock = chrono::steady_clock;

constexpr uint32_t WARMUP_RUNS = 10;

static int32_t bytes_to_int(const unsigned char* bytes)
{
    return static_cast<int32_t>(
        (static_cast<uint32_t>(bytes[0]) << 24) |
        (static_cast<uint32_t>(bytes[1]) << 16) |
        (static_cast<uint32_t>(bytes[2]) << 8) |
        static_cast<uint32_t>(bytes[3]));
}

static vector<float> load_images(const string& path, uint32_t count)
{
    ifstream file(path, ios::binary);
    if (!file)
        throw runtime_error("Cannot open image file: " + path);

    unsigned char header[16];
    file.read(reinterpret_cast<char*>(header), sizeof(header));

    if (file.gcount() != static_cast<streamsize>(sizeof(header)))
        throw runtime_error("Invalid MNIST image header");

    const uint32_t available_images =
        static_cast<uint32_t>(bytes_to_int(header + 4));

    const size_t rows =
        static_cast<size_t>(bytes_to_int(header + 8));

    const size_t columns =
        static_cast<size_t>(bytes_to_int(header + 12));

    if (count > available_images)
        throw runtime_error("Requested image count exceeds dataset size");

    const size_t image_size = rows * columns;

    vector<float> images(static_cast<size_t>(count) * image_size);
    vector<uint8_t> raw(image_size);

    for (uint32_t i = 0; i < count; ++i) {
        file.read(reinterpret_cast<char*>(raw.data()),
                  static_cast<streamsize>(raw.size()));

        if (file.gcount() != static_cast<streamsize>(raw.size()))
            throw runtime_error("Unexpected end of MNIST image file");

        for (size_t j = 0; j < image_size; ++j) {
            images[static_cast<size_t>(i) * image_size + j] =
                static_cast<float>(raw[j]) / 255.0f;
        }
    }

    return images;
}

int main(int argc, char* argv[])
{
    if (argc < 4 || argc > 5) {
        cerr << "Usage: " << argv[0]
             << " <xmodel> <images> <num_images> [repetitions]\n";
        return 1;
    }

    try {
        const string xmodel_path = argv[1];
        const string image_path = argv[2];
        const uint32_t image_count =
            static_cast<uint32_t>(stoul(argv[3]));

        const uint32_t repetitions =
            argc == 5 ? static_cast<uint32_t>(stoul(argv[4])) : 1;

        if (image_count == 0 || repetitions == 0)
            throw runtime_error(
                "num_images and repetitions must be greater than zero");

        const auto images = load_images(image_path, image_count);

        // Initialise DPU runner.
        auto graph = xir::Graph::deserialize(xmodel_path);
        auto attrs = xir::Attrs::create();
        auto subgraphs = get_dpu_subgraph(graph.get());

        if (subgraphs.empty())
            throw runtime_error("No DPU subgraph found in xmodel");

        auto runner =
            vart::RunnerExt::create_runner(subgraphs[0], attrs.get());

        const auto input_tensors = runner->get_input_tensors();
        const auto output_tensors = runner->get_output_tensors();

        if (input_tensors.empty() || output_tensors.empty())
            throw runtime_error("DPU runner has no input or output tensor");

        const auto input_shape = input_tensors[0]->get_shape();
        const auto output_shape = output_tensors[0]->get_shape();

        const size_t batch_size =
            static_cast<size_t>(input_shape[0]);

        const size_t input_size =
            input_tensors[0]->get_element_num() / batch_size;

        const size_t output_size =
            output_tensors[0]->get_element_num() / batch_size;

        vector<float> batch_input(batch_size * input_size);
        vector<float> dpu_output(batch_size * output_size);

        auto input_tensor = shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                input_tensors[0]->get_name(),
                input_shape,
                xir::DataType{xir::DataType::FLOAT, 32U}));

        auto output_tensor = shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                output_tensors[0]->get_name(),
                output_shape,
                xir::DataType{xir::DataType::FLOAT, 32U}));

        auto input_buffer = make_unique<CpuFlatTensorBuffer>(
            batch_input.data(), input_tensor.get());

        auto output_buffer = make_unique<CpuFlatTensorBuffer>(
            dpu_output.data(), output_tensor.get());

        vector<vart::TensorBuffer*> inputs{
            input_buffer.get()
        };

        vector<vart::TensorBuffer*> outputs{
            output_buffer.get()
        };

        auto execute_dataset = [&](bool measure) -> double {
            double dpu_ms = 0.0;

            for (uint32_t base = 0;
                 base < image_count;
                 base += static_cast<uint32_t>(batch_size)) {

                const size_t run_size = min<size_t>(
                    batch_size, image_count - base);

                fill(batch_input.begin(),
                     batch_input.end(),
                     0.0f);

                copy_n(
                    images.data() +
                        static_cast<size_t>(base) * input_size,
                    run_size * input_size,
                    batch_input.data());

                const auto dpu_start = Clock::now();

                const auto job =
                    runner->execute_async(inputs, outputs);

                runner->wait(job.first, -1);

                const auto dpu_end = Clock::now();

                if (measure) {
                    dpu_ms += chrono::duration<double, milli>(
                        dpu_end - dpu_start).count();
                }
            }

            return dpu_ms;
        };

        // Warm up DPU, XRT, caches and buffers.
        for (uint32_t i = 0; i < WARMUP_RUNS; ++i)
            execute_dataset(false);

        double total_dpu_ms = 0.0;

        cout << "MEASUREMENT_START" << endl;

        const auto window_start = Clock::now();

        for (uint32_t repeat = 0;
             repeat < repetitions;
             ++repeat) {
            total_dpu_ms += execute_dataset(true);
        }

        const auto window_end = Clock::now();

        cout << "MEASUREMENT_END" << endl;

        const uint64_t total_images =
            static_cast<uint64_t>(image_count) * repetitions;

        const uint64_t jobs_per_repetition =
            (static_cast<uint64_t>(image_count) +
             batch_size - 1) /
            batch_size;

        const uint64_t total_jobs =
            jobs_per_repetition * repetitions;

        const double active_window_ms =
            chrono::duration<double, milli>(
                window_end - window_start).count();

        cout << fixed << setprecision(6)
             << "BATCH_SIZE=" << batch_size << '\n'
             << "IMAGES=" << total_images << '\n'
             << "DPU_JOBS=" << total_jobs << '\n'
             << "ACTIVE_WINDOW_MS=" << active_window_ms << '\n'
             << "DPU_EXECUTE_TOTAL_MS=" << total_dpu_ms << '\n'
             << "DPU_MS_PER_JOB="
             << total_dpu_ms / static_cast<double>(total_jobs) << '\n'
             << "DPU_MS_PER_IMAGE="
             << total_dpu_ms / static_cast<double>(total_images) << '\n'
             << "WINDOW_MS_PER_IMAGE="
             << active_window_ms / static_cast<double>(total_images)
             << '\n';

        return 0;
    }
    catch (const exception& error) {
        cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}