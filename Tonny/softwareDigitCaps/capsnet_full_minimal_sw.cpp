#include <algorithm>
#include <chrono>
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
#include "vart/runner.hpp"
#include "vart/runner_ext.hpp"
#include "Accel_Wrapper3.hpp"
#include "DigitCaps.h"

using namespace std;
namespace fs = std::filesystem;
using Clock = chrono::steady_clock;

constexpr uint32_t WARMUP_RUNS = 10;
constexpr size_t WEIGHT_COUNT = DIGIT_CAPS_NUM_DIGITS * DIGIT_CAPS_INPUT_CAPSULES * DIGIT_CAPS_DIM_CAPSULE * DIGIT_CAPS_INPUT_DIM_CAPSULE;
constexpr size_t DIGITCAPS_OUTPUT_SIZE = DIGIT_CAPS_NUM_DIGITS * DIGIT_CAPS_DIM_CAPSULE;

static uint32_t read_be32(const unsigned char* bytes)
{
    return (uint32_t(bytes[0]) << 24) | (uint32_t(bytes[1]) << 16) | (uint32_t(bytes[2]) << 8) | uint32_t(bytes[3]);
}

static vector<float> load_images(const string& path, uint32_t count)
{
    ifstream file(path, ios::binary);

    if (!file) {
        throw runtime_error("Cannot open image file: " + path);
    }

    unsigned char header[16];

    if (!file.read(reinterpret_cast<char*>(header), sizeof(header))) {
        throw runtime_error("Cannot read image header: " + path);
    }

    const uint32_t available = read_be32(header + 4);
    const size_t image_size = size_t(read_be32(header + 8)) * read_be32(header + 12);

    if (count > available) {
        throw runtime_error("Requested more images than available");
    }

    vector<float> images(size_t(count) * image_size);
    vector<uint8_t> raw(image_size);

    for (uint32_t i = 0; i < count; ++i) {
        if (!file.read(reinterpret_cast<char*>(raw.data()), raw.size())) {
            throw runtime_error("Not enough image data");
        }

        for (size_t j = 0; j < image_size; ++j) {
            images[size_t(i) * image_size + j] = float(raw[j]) / 255.0f;
        }
    }

    return images;
}

static vector<uint8_t> load_labels(const string& path, uint32_t count)
{
    ifstream file(path, ios::binary);

    if (!file) {
        throw runtime_error("Cannot open label file: " + path);
    }

    unsigned char header[8];

    if (!file.read(reinterpret_cast<char*>(header), sizeof(header))) {
        throw runtime_error("Cannot read label header: " + path);
    }

    if (count > read_be32(header + 4)) {
        throw runtime_error("Requested more labels than available");
    }

    vector<uint8_t> labels(count);

    if (!file.read(reinterpret_cast<char*>(labels.data()), labels.size())) {
        throw runtime_error("Not enough label data");
    }

    return labels;
}

static vector<float> load_weights(const string& path)
{
    ifstream file(path);

    if (!file) {
        throw runtime_error("Cannot open weight file: " + path);
    }

    vector<float> weights(WEIGHT_COUNT);

    for (size_t i = 0; i < weights.size(); ++i) {
        if (!(file >> weights[i])) {
            throw runtime_error("Invalid weight file at index " + to_string(i));
        }
    }

    return weights;
}

int main(int argc, char* argv[])
{
    if (argc < 7 || argc > 9) {
        cerr << "Usage: " << argv[0] << " <xmodel> <xclbin> <images> <float_weights.txt> <image_count> <labels> [repetitions] [output_dir]\n";
        return 1;
    }

    try {
        const uint32_t image_count = uint32_t(stoul(argv[5]));
        const uint32_t repetitions = argc > 7 ? uint32_t(stoul(argv[7])) : 1;
        const fs::path output_dir = argc > 8 ? fs::path(argv[8]) : fs::path("intermediate_results");

        if (!image_count || !repetitions) {
            throw runtime_error("image_count and repetitions must be positive");
        }

        const auto images = load_images(argv[3], image_count);
        auto weights = load_weights(argv[4]);
        const auto labels = load_labels(argv[6], image_count);

        auto graph = xir::Graph::deserialize(argv[1]);
        auto attrs = xir::Attrs::create();
        auto subgraphs = get_dpu_subgraph(graph.get());

        if (subgraphs.empty()) {
            throw runtime_error("No DPU subgraph found");
        }

        auto runner = vart::RunnerExt::create_runner(subgraphs[0], attrs.get());

        Accel_Wrapper3 accel(argv[2]);
        accel.initialise_primary_squash_kernel();
        accel.initialise_capsnet_length_kernel();

        const auto input_tensors = runner->get_input_tensors();
        const auto output_tensors = runner->get_output_tensors();
        const auto input_shape = input_tensors[0]->get_shape();
        const auto output_shape = output_tensors[0]->get_shape();
        const size_t batch_size = input_shape[0];
        const size_t input_size = input_tensors[0]->get_element_num() / batch_size;
        const size_t output_size = output_tensors[0]->get_element_num() / batch_size;

        vector<float> batch_input(batch_size * input_size);
        vector<float> dpu_output(batch_size * output_size);
        vector<float> squash_output(wrapper_constants_v3::PRIMARY_SQUASH_OUTPUT_COUNT);
        vector<float> digitcaps_output(DIGITCAPS_OUTPUT_SIZE);
        vector<float> length_output(wrapper_constants_v3::CAPSNET_LENGTH_OUTPUT_COUNT);
        vector<float> saved_length(size_t(image_count) * length_output.size());

        auto input_tensor = shared_ptr<xir::Tensor>(xir::Tensor::create(input_tensors[0]->get_name(), input_shape, xir::DataType{xir::DataType::FLOAT, 32U}));
        auto output_tensor = shared_ptr<xir::Tensor>(xir::Tensor::create(output_tensors[0]->get_name(), output_shape, xir::DataType{xir::DataType::FLOAT, 32U}));
        auto input_buffer = make_unique<CpuFlatTensorBuffer>(batch_input.data(), input_tensor.get());
        auto output_buffer = make_unique<CpuFlatTensorBuffer>(dpu_output.data(), output_tensor.get());

        vector<vart::TensorBuffer*> inputs{input_buffer.get()};
        vector<vart::TensorBuffer*> outputs{output_buffer.get()};

        auto execute_all = [&](bool save)
        {
            for (size_t base = 0; base < image_count; base += batch_size) {
                const size_t run_size = min(batch_size, size_t(image_count) - base);

                fill(batch_input.begin(), batch_input.end(), 0.0f);
                copy_n(images.data() + base * input_size, run_size * input_size, batch_input.data());

                const auto job = runner->execute_async(inputs, outputs);
                runner->wait(job.first, -1);

                for (size_t i = 0; i < run_size; ++i) {
                    accel.update_primary_squash_kernel(dpu_output.data() + i * output_size);
                    accel.execute_primary_squash_kernel(squash_output.data());
                    dynamic_routing(squash_output.data(), weights.data(), digitcaps_output.data());
                    accel.update_capsnet_length_kernel(digitcaps_output.data());
                    accel.execute_capsnet_length_kernel(length_output.data());

                    if (save) {
                        copy(length_output.begin(), length_output.end(), saved_length.begin() + (base + i) * length_output.size());
                    }
                }
            }
        };

        for (uint32_t i = 0; i < WARMUP_RUNS; ++i) {
            execute_all(false);
        }

        cout << "MEASUREMENT_START" << endl;

        const auto start = Clock::now();

        for (uint32_t i = 0; i < repetitions; ++i) {
            execute_all(i + 1 == repetitions);
        }

        const auto end = Clock::now();

        cout << "MEASUREMENT_END" << endl;

        const uint64_t runs = uint64_t(image_count) * repetitions;
        const double total_ms = chrono::duration<double, milli>(end - start).count();

        cout << fixed << setprecision(6);
        cout << "RUNS=" << runs << '\n';
        cout << "ACTIVE_WINDOW_MS=" << total_ms << '\n';
        cout << "LATENCY_PER_INFERENCE_MS=" << total_ms / runs << '\n';

        fs::create_directories(output_dir);

        ofstream file(output_dir / "capsnet_length_output.txt");

        if (!file) {
            throw runtime_error("Cannot create output file");
        }

        file << fixed << setprecision(10);

        size_t correct = 0;

        for (uint32_t i = 0; i < image_count; ++i) {
            const float* prediction = saved_length.data() + size_t(i) * length_output.size();

            for (size_t digit = 0; digit < length_output.size(); ++digit) {
                if (digit) {
                    file << ' ';
                }

                file << prediction[digit];
            }

            file << '\n';

            const size_t predicted = max_element(prediction, prediction + length_output.size()) - prediction;
            correct += predicted == labels[i];
        }

        cout << "Accuracy=" << 100.0 * correct / image_count << "%\n";

        return 0;
    }
    catch (const exception& error) {
        cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}