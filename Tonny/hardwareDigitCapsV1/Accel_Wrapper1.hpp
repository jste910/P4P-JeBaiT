#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

#include "wrapper_constants_v1.h"
#include "xrt/xrt_bo.h"
#include "xrt/xrt_device.h"
#include "xrt/xrt_kernel.h"

static constexpr float FIXED_SCALE = 65536.0f;
class Accel_Wrapper1 {
public: 
    //constructors
    xrt :: device device;
    xrt :: uuid xclbin_uuid;
    xrt :: kernel primary_squash_kernel, digitcaps_kernel, capsnet_length_kernel;
    xrt :: bo primary_squash_input_bo, primary_squash_output_bo;
    xrt :: bo digitcaps_input_bo, digitcaps_weight_bo, digitcaps_output_bo;
    xrt :: bo capsnet_length_input_bo, capsnet_length_output_bo;
    xrt :: run primary_squash_run, digitcaps_run, capsnet_length_run;
    Accel_Wrapper1(const std::string& xclbin_path)
    {
        device = xrt :: device(0);
        xclbin_uuid = device.load_xclbin(xclbin_path);
    }

    void initialise_primary_squash_kernel()
    {
        primary_squash_kernel = xrt::kernel(device, xclbin_uuid, "primary_squash_accel");
        primary_squash_input_bo = xrt::bo(device, wrapper_constants_v1::PRIMARY_SQUASH_INPUT_BYTES,primary_squash_kernel.group_id(0));
        primary_squash_output_bo = xrt::bo(device, wrapper_constants_v1::PRIMARY_SQUASH_OUTPUT_BYTES,primary_squash_kernel.group_id(1));
        
    }
    void update_primary_squash_kernel(const float* primary_squash_input)
    {
        std :: vector<int32_t> primary_squash_input_fixed (wrapper_constants_v1::PRIMARY_SQUASH_INPUT_COUNT);
        convert_float_to_fixed32_16(primary_squash_input,primary_squash_input_fixed.data(),primary_squash_input_fixed.size());

        primary_squash_input_bo.write(primary_squash_input_fixed.data(), wrapper_constants_v1::PRIMARY_SQUASH_INPUT_BYTES,0);
        primary_squash_input_bo.sync(XCL_BO_SYNC_BO_TO_DEVICE);
    }

    void execute_primary_squash_kernel(float* primary_squash_output)
    {
        std :: vector<int32_t> primary_squash_output_fixed (wrapper_constants_v1::PRIMARY_SQUASH_OUTPUT_COUNT);

        primary_squash_run = primary_squash_kernel(primary_squash_input_bo,primary_squash_output_bo);
        primary_squash_run.wait();
        primary_squash_output_bo.sync(XCL_BO_SYNC_BO_FROM_DEVICE);
        primary_squash_output_bo.read(primary_squash_output_fixed.data(), wrapper_constants_v1::PRIMARY_SQUASH_OUTPUT_BYTES,0);
        

        convert_fixed32_16_to_float(primary_squash_output_fixed.data(), primary_squash_output, primary_squash_output_fixed.size());
    }

    void initialise_digitcaps_kernel(const float* digitcaps_weight)
    {
        std::vector<int32_t> digitcaps_weight_fixed(wrapper_constants_v1::DIGITCAPS_WEIGHT_COUNT);
        convert_float_to_fixed32_16(digitcaps_weight,digitcaps_weight_fixed.data(),digitcaps_weight_fixed.size());

        digitcaps_kernel = xrt::kernel(device, xclbin_uuid, "digitcaps_accel");
        digitcaps_input_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_INPUT_BYTES,digitcaps_kernel.group_id(0));
        digitcaps_weight_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_WEIGHT_BYTES,digitcaps_kernel.group_id(1));
        digitcaps_output_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_OUTPUT_BYTES,digitcaps_kernel.group_id(2));
        
        digitcaps_weight_bo.write(digitcaps_weight_fixed.data(),wrapper_constants_v1::DIGITCAPS_WEIGHT_BYTES,0);
        digitcaps_weight_bo.sync(XCL_BO_SYNC_BO_TO_DEVICE);
    }

    void initialise_digitcaps_kernel_fixed(const int32_t* digitcaps_weight_fixed)
    {
        digitcaps_kernel = xrt::kernel(device, xclbin_uuid, "digitcaps_accel");
        digitcaps_input_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_INPUT_BYTES,digitcaps_kernel.group_id(0));
        digitcaps_weight_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_WEIGHT_BYTES,digitcaps_kernel.group_id(1));
        digitcaps_output_bo = xrt::bo(device, wrapper_constants_v1::DIGITCAPS_OUTPUT_BYTES,digitcaps_kernel.group_id(2));
        
        digitcaps_weight_bo.write(digitcaps_weight_fixed,wrapper_constants_v1::DIGITCAPS_WEIGHT_BYTES,0);
        digitcaps_weight_bo.sync(XCL_BO_SYNC_BO_TO_DEVICE);
    }

    void update_digitcaps_kernel(const float* digitcaps_input)
    {
        std::vector<int32_t> digitcaps_input_fixed(wrapper_constants_v1::DIGITCAPS_INPUT_COUNT);
        convert_float_to_fixed32_16(digitcaps_input,digitcaps_input_fixed.data(),digitcaps_input_fixed.size());

        digitcaps_input_bo.write(digitcaps_input_fixed.data(),wrapper_constants_v1::DIGITCAPS_INPUT_BYTES,0);
        digitcaps_input_bo.sync(XCL_BO_SYNC_BO_TO_DEVICE);
    }

    void run_digitcaps_kernel()
    {
        digitcaps_run = digitcaps_kernel(digitcaps_input_bo,digitcaps_weight_bo,digitcaps_output_bo);
        digitcaps_run.wait();
    }

    void read_digitcaps_kernel(float* digitcaps_output)
    {
        std::vector<int32_t> digitcaps_output_fixed(wrapper_constants_v1::DIGITCAPS_OUTPUT_COUNT);

        digitcaps_output_bo.sync(XCL_BO_SYNC_BO_FROM_DEVICE);
        digitcaps_output_bo.read(digitcaps_output_fixed.data(),wrapper_constants_v1::DIGITCAPS_OUTPUT_BYTES,0);

        convert_fixed32_16_to_float(digitcaps_output_fixed.data(),digitcaps_output,digitcaps_output_fixed.size());
    }

    void execute_digitcaps_kernel(float* digitcaps_output)
    {
        run_digitcaps_kernel();
        read_digitcaps_kernel(digitcaps_output);
    }

    void initialise_capsnet_length_kernel()
    {
        capsnet_length_kernel = xrt :: kernel(device,xclbin_uuid,"capsnet_length_accel");
        capsnet_length_input_bo = xrt :: bo(device, wrapper_constants_v1::CAPSNET_LENGTH_INPUT_BYTES,capsnet_length_kernel.group_id(0));
        capsnet_length_output_bo = xrt :: bo(device, wrapper_constants_v1::CAPSNET_LENGTH_OUTPUT_BYTES,capsnet_length_kernel.group_id(1));
    }

    void update_capsnet_length_kernel(const float* capsnet_length_input)
    {
        std::vector<int32_t> capsnet_length_input_fixed(wrapper_constants_v1::CAPSNET_LENGTH_INPUT_COUNT);
        convert_float_to_fixed32_16(capsnet_length_input,capsnet_length_input_fixed.data(),capsnet_length_input_fixed.size());

        capsnet_length_input_bo.write(capsnet_length_input_fixed.data(), wrapper_constants_v1::CAPSNET_LENGTH_INPUT_BYTES,0);
        capsnet_length_input_bo.sync(XCL_BO_SYNC_BO_TO_DEVICE);
    }

    void execute_capsnet_length_kernel(float* capsnet_length_output)
    {
        std::vector<int32_t> capsnet_length_output_fixed(wrapper_constants_v1::CAPSNET_LENGTH_OUTPUT_COUNT);

        capsnet_length_run = capsnet_length_kernel(capsnet_length_input_bo,capsnet_length_output_bo);
        capsnet_length_run.wait();
        capsnet_length_output_bo.sync(XCL_BO_SYNC_BO_FROM_DEVICE);
        capsnet_length_output_bo.read(capsnet_length_output_fixed.data(),wrapper_constants_v1::CAPSNET_LENGTH_OUTPUT_BYTES,0);
        convert_fixed32_16_to_float(capsnet_length_output_fixed.data(),capsnet_length_output,capsnet_length_output_fixed.size());
    }


    static int32_t float_to_fixed(float x)
    {
        return static_cast<int32_t>(std::llround(x * FIXED_SCALE));
    }

    static float fixed_to_float(int32_t x)
    {
        return static_cast<float>(x) / FIXED_SCALE;
    }

    static void convert_float_to_fixed32_16(const float* input, int32_t* output, std::size_t size)
    {
        for (std::size_t i = 0; i < size; ++i) {
            output[i] = float_to_fixed(input[i]);
        }
    }
    static void convert_fixed32_16_to_float(const int32_t* input, float* output, std::size_t size)
    {
        for (std::size_t i = 0; i < size; ++i) {
            output[i] = fixed_to_float(input[i]);
        }
    }


};
