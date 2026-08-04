#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "common.h"
#include "vart/runner.hpp"
#include "vart/runner_ext.hpp"
#include "Accel_Wrapper.hpp"

using namespace std;
using Clock = chrono::steady_clock;

constexpr uint32_t WARMUP_RUNS = 10;
constexpr uint32_t IDLE_SETTLING_SECONDS = 1;
constexpr uint32_t IDLE_MEASUREMENT_SECONDS = 20;

static int32_t bytes_to_int(const unsigned char* bytes)
{
    return static_cast<int32_t>(
        (static_cast<uint32_t>(bytes[0]) << 24) |
        (static_cast<uint32_t>(bytes[1]) << 16) |
        (static_cast<uint32_t>(bytes[2]) << 8) |
        static_cast<uint32_t>(bytes[3]));
}

static vector<float> load_images(
    const string& path,
    uint32_t count)
{
    ifstream file(path, ios::binary);

    if (!file)
        throw runtime_error(
            "Cannot open MNIST image file: " + path);

    unsigned char header[16];

    file.read(
        reinterpret_cast<char*>(header),
        sizeof(header));

    if (!file)
        throw runtime_error(
            "Cannot read MNIST image header: " + path);

    const uint32_t available =
        static_cast<uint32_t>(
            bytes_to_int(header + 4));

    const size_t image_size =
        static_cast<size_t>(
            bytes_to_int(header + 8)) *
        static_cast<size_t>(
            bytes_to_int(header + 12));

    if (count > available)
        throw runtime_error(
            "Requested more MNIST images than available");

    vector<float> images(
        static_cast<size_t>(count) * image_size);

    vector<uint8_t> raw(image_size);

    for (uint32_t i = 0; i < count; ++i) {
        file.read(
            reinterpret_cast<char*>(raw.data()),
            raw.size());

        if (!file)
            throw runtime_error(
                "Failed while reading MNIST images");

        for (size_t j = 0; j < image_size; ++j) {
            images[
                static_cast<size_t>(i) *
                    image_size +
                j
            ] = raw[j] / 255.0f;
        }
    }

    return images;
}

static vector<float> load_values(const string& path)
{
    ifstream file(path);

    if (!file)
        throw runtime_error(
            "Cannot open weight file: " + path);

    vector<float> values;
    float value;

    while (file >> value)
        values.push_back(value);

    if (values.empty())
        throw runtime_error(
            "No weights loaded from: " + path);

    return values;
}

int main(int argc, char* argv[])
{
    if (argc < 6 || argc > 9) {
        cerr
            << "Usage: ./capsnet_idle.exe "
            << "<xmodel> <xclbin> <images> <weights> "
            << "<num_images> "
            << "[labels_ignored] "
            << "[repetitions_ignored] "
            << "[output_dir_ignored]\n";

        return 1;
    }

    const string xmodel_path = argv[1];
    const string xclbin_path = argv[2];
    const string image_path = argv[3];
    const string weight_path = argv[4];

    const uint32_t image_count =
        static_cast<uint32_t>(
            stoul(argv[5]));

    // Optional arguments are accepted only for compatibility
    // with the existing Python command builder.
    if (argc > 6)
        (void)argv[6];

    if (argc > 7)
        (void)argv[7];

    if (argc > 8)
        (void)argv[8];

    const auto images =
        load_images(
            image_path,
            image_count);

    const auto weights =
        load_values(
            weight_path);

    auto graph =
        xir::Graph::deserialize(
            xmodel_path);

    auto attrs =
        xir::Attrs::create();

    auto subgraphs =
        get_dpu_subgraph(
            graph.get());

    if (subgraphs.empty())
        throw runtime_error(
            "No DPU subgraph found");

    auto runner =
        vart::RunnerExt::create_runner(
            subgraphs[0],
            attrs.get());

    Accel_Wrapper accel(xclbin_path);

    accel.initialise_primary_squash_kernel();

    accel.initialise_digitcaps_kernel(
        weights.data());

    accel.initialise_capsnet_length_kernel();

    const auto input_tensors =
        runner->get_input_tensors();

    const auto output_tensors =
        runner->get_output_tensors();

    const auto input_shape =
        input_tensors[0]->get_shape();

    const auto output_shape =
        output_tensors[0]->get_shape();

    const size_t batch_size =
        input_shape[0];

    const size_t input_size =
        input_tensors[0]->get_element_num() /
        batch_size;

    const size_t output_size =
        output_tensors[0]->get_element_num() /
        batch_size;

    vector<float> batch_input(
        batch_size * input_size);

    vector<float> dpu_output(
        batch_size * output_size);

    vector<float> squash_output(
        wrapper_constants::
            PRIMARY_SQUASH_OUTPUT_COUNT);

    vector<float> digitcaps_output(
        wrapper_constants::
            DIGITCAPS_OUTPUT_COUNT);

    vector<float> length_output(
        wrapper_constants::
            CAPSNET_LENGTH_OUTPUT_COUNT);

    auto input_tensor =
        shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                input_tensors[0]->get_name(),
                input_shape,
                xir::DataType{
                    xir::DataType::FLOAT,
                    32U}));

    auto output_tensor =
        shared_ptr<xir::Tensor>(
            xir::Tensor::create(
                output_tensors[0]->get_name(),
                output_shape,
                xir::DataType{
                    xir::DataType::FLOAT,
                    32U}));

    auto input_buffer =
        make_unique<CpuFlatTensorBuffer>(
            batch_input.data(),
            input_tensor.get());

    auto output_buffer =
        make_unique<CpuFlatTensorBuffer>(
            dpu_output.data(),
            output_tensor.get());

    vector<vart::TensorBuffer*> inputs{
        input_buffer.get()
    };

    vector<vart::TensorBuffer*> outputs{
        output_buffer.get()
    };

    auto execute_all =
        [&]()
        {
            for (uint32_t base = 0;
                 base < image_count;
                 base += batch_size)
            {
                const size_t run_size =
                    min<size_t>(
                        batch_size,
                        image_count - base);

                fill(
                    batch_input.begin(),
                    batch_input.end(),
                    0.0f);

                copy_n(
                    images.data() +
                        static_cast<size_t>(base) *
                            input_size,
                    run_size * input_size,
                    batch_input.data());

                const auto job =
                    runner->execute_async(
                        inputs,
                        outputs);

                runner->wait(
                    job.first,
                    -1);

                for (size_t i = 0;
                     i < run_size;
                     ++i)
                {
                    const float* current_dpu =
                        dpu_output.data() +
                        i * output_size;

                    accel.update_primary_squash_kernel(
                        current_dpu);

                    accel.execute_primary_squash_kernel(
                        squash_output.data());

                    accel.update_digitcaps_kernel(
                        squash_output.data());

                    accel.execute_digitcaps_kernel(
                        digitcaps_output.data());

                    accel.update_capsnet_length_kernel(
                        digitcaps_output.data());

                    accel.execute_capsnet_length_kernel(
                        length_output.data());
                }
            }
        };

    // Standardized thermal/runtime warm-up.
    for (uint32_t i = 0;
         i < WARMUP_RUNS;
         ++i)
    {
        execute_all();
    }

    // Let outstanding activity settle before idle sampling.
    this_thread::sleep_for(
        chrono::seconds(
            IDLE_SETTLING_SECONDS));

    // No inference or file I/O occurs inside this window.
    cout << "MEASUREMENT_START" << endl;

    const auto idle_start =
        Clock::now();

    this_thread::sleep_for(
        chrono::seconds(
            IDLE_MEASUREMENT_SECONDS));

    const auto idle_end =
        Clock::now();

    cout << "MEASUREMENT_END" << endl;

    const double idle_window_ms =
        chrono::duration<double, milli>(
            idle_end - idle_start).count();

    cout << fixed << setprecision(6)
         << "MEASUREMENT_TYPE=CONFIGURED_IDLE\n"
         << "IDLE_WINDOW_MS="
         << idle_window_ms
         << '\n';

    return 0;
}
