#ifndef WRAPPER_CONSTANTS_H
#define WRAPPER_CONSTANTS_H

#include <cstddef>
#include <cstdint>

#include "constants.h"

/*
 * Host-wrapper constants derived from constants.h.
 *
 * All *_COUNT constants represent numbers of elements.
 * All *_BYTES constants represent buffer sizes in bytes.
 */

namespace wrapper_constants
{

// -----------------------------------------------------------------------------
// Fixed-point representation
// -----------------------------------------------------------------------------

static constexpr int FIXED_TOTAL_BITS = 32;
static constexpr int FIXED_FRACTIONAL_BITS = 16;

static constexpr float FIXED_SCALE =
    static_cast<float>(1U << FIXED_FRACTIONAL_BITS);

// -----------------------------------------------------------------------------
// Input image
// -----------------------------------------------------------------------------

static constexpr std::size_t INPUT_IMAGE_COUNT =
    static_cast<std::size_t>(IN_IMG_ROWS) *
    IN_IMG_COLS *
    IN_IMG_DEPTH;

static constexpr std::size_t INPUT_IMAGE_BYTES =
    INPUT_IMAGE_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// Conv1 output
// Shape: 20 x 20 x 256
// -----------------------------------------------------------------------------

static constexpr std::size_t CONV1_OUTPUT_COUNT =
    static_cast<std::size_t>(CONV1_OUTPUT_WIDTH) *
    CONV1_OUTPUT_LENGTH *
    CONV1_FILTERS;

static constexpr std::size_t CONV1_OUTPUT_BYTES =
    CONV1_OUTPUT_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// PrimaryCaps convolution output
// Shape: 6 x 6 x 256
// -----------------------------------------------------------------------------

static constexpr std::size_t PRIMARY_CAPS_CONV_OUTPUT_COUNT =
    static_cast<std::size_t>(PRIMARY_CAPS_CONV_WIDTH) *
    PRIMARY_CAPS_CONV_LENGTH *
    PRIMARY_CAPS_CONV_DEPTH;

static constexpr std::size_t PRIMARY_CAPS_CONV_OUTPUT_BYTES =
    PRIMARY_CAPS_CONV_OUTPUT_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// PrimaryCaps reshaped/squashed tensor
//
// Shape:
//   1152 capsules x 8 values per capsule
//
// DIGIT_CAPS_INPUT_CAPSULES is derived from:
//   6 x 6 x 32 = 1152 capsules
// -----------------------------------------------------------------------------

static constexpr std::size_t PRIMARY_SQUASH_INPUT_COUNT =
    static_cast<std::size_t>(DIGIT_CAPS_INPUT_CAPSULES) *
    PRIMARY_CAPS_CAPSULE_DIM;

static constexpr std::size_t PRIMARY_SQUASH_OUTPUT_COUNT =
    static_cast<std::size_t>(DIGIT_CAPS_INPUT_CAPSULES) *
    PRIMARY_CAPS_CAPSULE_DIM;

static constexpr std::size_t PRIMARY_SQUASH_INPUT_BYTES =
    PRIMARY_SQUASH_INPUT_COUNT * sizeof(int32_t);

static constexpr std::size_t PRIMARY_SQUASH_OUTPUT_BYTES =
    PRIMARY_SQUASH_OUTPUT_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// DigitCaps
//
// Input shape:
//   1152 x 8
//
// Weight shape expected by the accelerator:
//   10 x 1152 x 16 x 8
//
// Output shape:
//   10 x 16
// -----------------------------------------------------------------------------

static constexpr std::size_t DIGITCAPS_INPUT_COUNT =
    static_cast<std::size_t>(DIGIT_CAPS_INPUT_CAPSULES) *
    DIGIT_CAPS_INPUT_DIM_CAPSULE;

static constexpr std::size_t DIGITCAPS_WEIGHT_COUNT =
    static_cast<std::size_t>(DIGIT_CAPS_NUM_DIGITS) *
    DIGIT_CAPS_INPUT_CAPSULES *
    DIGIT_CAPS_DIM_CAPSULE *
    DIGIT_CAPS_INPUT_DIM_CAPSULE;

static constexpr std::size_t DIGITCAPS_OUTPUT_COUNT =
    static_cast<std::size_t>(DIGIT_CAPS_NUM_DIGITS) *
    DIGIT_CAPS_DIM_CAPSULE;

static constexpr std::size_t DIGITCAPS_INPUT_BYTES =
    DIGITCAPS_INPUT_COUNT * sizeof(int32_t);

static constexpr std::size_t DIGITCAPS_WEIGHT_BYTES =
    DIGITCAPS_WEIGHT_COUNT * sizeof(int8_t);

static constexpr std::size_t DIGITCAPS_OUTPUT_BYTES =
    DIGITCAPS_OUTPUT_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// CapsNet length layer
//
// Input shape:
//   10 x 16
//
// Output shape:
//   10 scalar capsule lengths
// -----------------------------------------------------------------------------

static constexpr std::size_t CAPSNET_LENGTH_INPUT_COUNT =
    DIGITCAPS_OUTPUT_COUNT;

static constexpr std::size_t CAPSNET_LENGTH_OUTPUT_COUNT =
    DIGIT_CAPS_NUM_DIGITS;

static constexpr std::size_t CAPSNET_LENGTH_INPUT_BYTES =
    CAPSNET_LENGTH_INPUT_COUNT * sizeof(int32_t);

static constexpr std::size_t CAPSNET_LENGTH_OUTPUT_BYTES =
    CAPSNET_LENGTH_OUTPUT_COUNT * sizeof(int32_t);

// -----------------------------------------------------------------------------
// Compile-time consistency checks
// -----------------------------------------------------------------------------

static_assert(
    PRIMARY_CAPS_CAPSULE_DIM ==
        DIGIT_CAPS_INPUT_DIM_CAPSULE,
    "PrimaryCaps output dimension must match DigitCaps input dimension"
);

static_assert(
    PRIMARY_SQUASH_OUTPUT_COUNT ==
        DIGITCAPS_INPUT_COUNT,
    "PrimarySquash output size must match DigitCaps input size"
);

static_assert(
    DIGITCAPS_OUTPUT_COUNT ==
        CAPSNET_LENGTH_INPUT_COUNT,
    "DigitCaps output size must match CapsNetLength input size"
);

static_assert(
    DIGIT_CAPS_INPUT_CAPSULES ==
        PRIMARY_CAPS_CONV_WIDTH *
        PRIMARY_CAPS_CONV_LENGTH *
        PRIMARY_CAPS_CAPSULES,
    "DigitCaps input capsule count does not match PrimaryCaps dimensions"
);

} // namespace wrapper_constants

#endif // WRAPPER_CONSTANTS_H