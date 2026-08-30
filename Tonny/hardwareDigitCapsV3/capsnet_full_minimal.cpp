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
#include "vart/runner.hpp"
#include "vart/runner_ext.hpp"
#include "Accel_Wrapper3.hpp"

using namespace std;
namespace fs = std::filesystem;
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
    unsigned char header[16];
    file.read(reinterpret_cast<char*>(header), sizeof(header));

    const size_t image_size =
        static_cast<size_t>(bytes_to_int(header + 8)) *
        bytes_to_int(header + 12);

    vector<float> images(static_cast<size_t>(count) * image_size);
    vector<uint8_t> raw(image_size);

    for (uint32_t i = 0; i < count; ++i) {
        file.read(reinterpret_cast<char*>(raw.data()), raw.size());

        for (size_t j = 0; j < image_size; ++j)
            images[static_cast<size_t>(i) * image_size + j] =
                raw[j] / 255.0f;
    }

    return images;
}

static vector<uint8_t> load_labels(const string& path, uint32_t count)
{
    ifstream file(path, ios::binary);
    unsigned char header[8];
    file.read(reinterpret_cast<char*>(header), sizeof(header));

    vector<uint8_t> labels(count);
    file.read(reinterpret_cast<char*>(labels.data()), labels.size());
    return labels;
}

static vector<float> load_values(const string& path)
{
    ifstream file(path);
    vector<float> values;
    float value;

    while (file >> value)
        values.push_back(value);

    return values;
}

static void dump(const fs::path& path, const float* data, size_t count)
{
    ofstream file(path);
    file << fixed << setprecision(10);

    for (size_t i = 0; i < count; ++i)
        file << data[i] << '\n';
}

int main(int argc, char* argv[])
{
    if (argc < 7 || argc > 9) {
        cerr
            << "Usage: ./CapsuleNetwork.exe "
            << "<xmodel> <xclbin> <images> <weights> "
            << "<num_images> <labels> "
            << "[repetitions] [output_dir]\n";
        return 1;
    }

    const string xmodel_path = argv[1];
    const string xclbin_path = argv[2];
    const string image_path = argv[3];
    const string weight_path = argv[4];
    const uint32_t image_count =
        static_cast<uint32_t>(stoul(argv[5]));
    const string label_path = argv[6];
    const uint32_t repetitions =
        argc > 7 ? static_cast<uint32_t>(stoul(argv[7])) : 1;
    const fs::path output_dir =
        argc > 8 ? fs::path(argv[8]) : fs::path("intermediate_results");

    const auto images = load_images(image_path, image_count);
    const auto labels = load_labels(label_path, image_count);
    const auto weights = load_values(weight_path);

    auto graph = xir::Graph::deserialize(xmodel_path);
    auto attrs = xir::Attrs::create();
    auto subgraphs = get_dpu_subgraph(graph.get());
    auto runner = vart::RunnerExt::create_runner(
        subgraphs[0],
        attrs.get());

    Accel_Wrapper3 accel(xclbin_path);
    accel.initialise_primary_squash_kernel();
    accel.initialise_digitcaps_kernel(weights.data());
    accel.initialise_capsnet_length_kernel();

    const auto input_tensors = runner->get_input_tensors();
    const auto output_tensors = runner->get_output_tensors();
    const auto input_shape = input_tensors[0]->get_shape();
    const auto output_shape = output_tensors[0]->get_shape();

    const size_t batch_size = input_shape[0];
    const size_t input_size =
        input_tensors[0]->get_element_num() / batch_size;
    const size_t output_size =
        output_tensors[0]->get_element_num() / batch_size;

    vector<float> batch_input(batch_size * input_size);
    vector<float> dpu_output(batch_size * output_size);
    vector<float> squash_output(
        wrapper_constants_v3::PRIMARY_SQUASH_OUTPUT_COUNT);
    vector<float> digitcaps_output(
        wrapper_constants_v3::DIGITCAPS_OUTPUT_COUNT);
    vector<float> length_output(
        wrapper_constants_v3::CAPSNET_LENGTH_OUTPUT_COUNT);

    vector<float> saved_dpu(
        static_cast<size_t>(image_count) * output_size);
    vector<float> saved_squash(
        static_cast<size_t>(image_count) * squash_output.size());
    vector<float> saved_digitcaps(
        static_cast<size_t>(image_count) * digitcaps_output.size());
    vector<float> saved_length(
        static_cast<size_t>(image_count) * length_output.size());

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
        batch_input.data(),
        input_tensor.get());

    auto output_buffer = make_unique<CpuFlatTensorBuffer>(
        dpu_output.data(),
        output_tensor.get());

    vector<vart::TensorBuffer*> inputs{input_buffer.get()};
    vector<vart::TensorBuffer*> outputs{output_buffer.get()};

    auto execute_all = [&](bool save)
    {
        for (uint32_t base = 0;
             base < image_count;
             base += batch_size)
        {
            const size_t run_size =
                min<size_t>(batch_size, image_count - base);

            fill(batch_input.begin(), batch_input.end(), 0.0f);

            copy_n(
                images.data() +
                    static_cast<size_t>(base) * input_size,
                run_size * input_size,
                batch_input.data());

            const auto job = runner->execute_async(inputs, outputs);
            runner->wait(job.first, -1);

            for (size_t i = 0; i < run_size; ++i) {
                const size_t image_index = base + i;
                const float* current_dpu =
                    dpu_output.data() + i * output_size;

                accel.update_primary_squash_kernel(current_dpu);
                accel.execute_primary_squash_kernel(
                    squash_output.data());

                accel.update_digitcaps_kernel(squash_output.data());
                accel.execute_digitcaps_kernel(
                    digitcaps_output.data());

                accel.update_capsnet_length_kernel(
                    digitcaps_output.data());
                accel.execute_capsnet_length_kernel(
                    length_output.data());

                if (save) {
                    copy_n(
                        current_dpu,
                        output_size,
                        saved_dpu.data() +
                            image_index * output_size);

                    copy(
                        squash_output.begin(),
                        squash_output.end(),
                        saved_squash.begin() +
                            image_index * squash_output.size());

                    copy(
                        digitcaps_output.begin(),
                        digitcaps_output.end(),
                        saved_digitcaps.begin() +
                            image_index * digitcaps_output.size());

                    copy(
                        length_output.begin(),
                        length_output.end(),
                        saved_length.begin() +
                            image_index * length_output.size());
                }
            }
        }
    };

    for (uint32_t i = 0; i < WARMUP_RUNS; ++i)
        execute_all(false);

    cout << "MEASUREMENT_START" << endl;
    const auto start = Clock::now();

    for (uint32_t repeat = 0;
         repeat < repetitions;
         ++repeat)
    {
        execute_all(repeat + 1 == repetitions);
    }

    const auto end = Clock::now();
    cout << "MEASUREMENT_END" << endl;

    const uint64_t runs =
        static_cast<uint64_t>(image_count) * repetitions;

    const double total_ms =
        chrono::duration<double, milli>(end - start).count();

    cout << fixed << setprecision(6)
         << "RUNS=" << runs << '\n'
         << "ACTIVE_WINDOW_MS=" << total_ms << '\n'
         << "LATENCY_PER_INFERENCE_MS="
         << total_ms / runs << '\n';

    fs::create_directories(output_dir);

    const fs::path result_path =
        output_dir / "capsnet_length_output.txt";

    ofstream result_file(result_path);

    if (!result_file)
        throw runtime_error(
            "Cannot open output file: " +
            result_path.string());

    result_file << fixed << setprecision(10);

    size_t correct = 0;

    for (uint32_t i = 0; i < image_count; ++i) {
        const float* prediction =
            saved_length.data() +
            static_cast<size_t>(i) * length_output.size();

        // One line per image, containing only the final 10 values.
        for (size_t digit = 0;
             digit < length_output.size();
             ++digit)
        {
            if (digit != 0)
                result_file << ' ';

            result_file << prediction[digit];
        }

        result_file << '\n';

        const size_t predicted =
            max_element(
                prediction,
                prediction + length_output.size()) -
            prediction;

        correct += predicted == labels[i];
    }

    result_file.close();

    cout << "Accuracy="
         << 100.0 *
                static_cast<double>(correct) /
                image_count
         << "%\n";

    return 0;
}