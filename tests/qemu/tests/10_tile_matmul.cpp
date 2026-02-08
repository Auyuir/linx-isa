// LinxISA Tile Block Tests (TAU bring-up)
//
// This suite exercises the builtin-based PTO→LinxISA tile lowering (no inline
// assembly / no raw-encoding stubs):
// - BSTART.TMA + B.IOT/B.IOTI: TLOAD/TSTORE
// - BSTART.CUBE(MAMULB/ACCCVT) + B.DIM + B.IOT: 8x8 i32 matmul in QEMU (TAU emulation)

#include "linx_test.h"

#define __LINX_TAU__ 1
#include <pto/linx/TileOps.hpp>

static void tile_matmul_ref_i32_8x8(int32_t out[64], const int32_t a[64], const int32_t b[64])
{
    for (unsigned i = 0; i < 8; i++) {
        for (unsigned j = 0; j < 8; j++) {
            int64_t acc = 0;
            for (unsigned k = 0; k < 8; k++) {
                acc += (int64_t)a[i * 8u + k] * (int64_t)b[k * 8u + j];
            }
            out[i * 8u + j] = (int32_t)acc;
        }
    }
}

extern "C" void run_tile_tests(void)
{
    test_suite_begin(0x0000000A);

    test_start(0x000A0001);
    uart_puts("PTO tile matmul (8x8 i32) ... ");

    alignas(16) static int32_t A[1024];
    alignas(16) static int32_t B[1024];
    alignas(16) static int32_t C[1024];
    alignas(16) static int32_t EXP[64];

    for (unsigned i = 0; i < 1024; i++) {
        A[i] = 0;
        B[i] = 0;
        C[i] = 0;
        if (i < 64) {
            A[i] = (int32_t)((int)i % 7 - 3);
            B[i] = (int32_t)((int)i % 5 - 2);
        }
    }
    for (unsigned i = 0; i < 64; i++) {
        EXP[i] = 0;
    }

    // Tiles are SSA values; LLVM register allocation assigns them to the
    // architectural tile register file (32 tiles: 4 hands × depth 8).
    auto tA = pto::linx::tload<0>(A);          // 4 KiB
    auto tB = pto::linx::tload<0>(B);          // 4 KiB
    auto tC = pto::linx::mamulb<8, 8, 8>(tA, tB); // 8x8 i32
    pto::linx::tstore<0>(C, tC);               // 4 KiB

    tile_matmul_ref_i32_8x8(EXP, A, B);
    for (unsigned i = 0; i < 64; i++) {
        TEST_EQ32((uint32_t)C[i], (uint32_t)EXP[i], 0x000A1000u + i);
    }

    test_pass();
}
