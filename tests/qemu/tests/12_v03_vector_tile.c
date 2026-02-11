/*
 * v0.3 Vector/Tile Block-Start Smoke Tests (strict profile)
 *
 * Bring-up goal:
 * - Ensure typed block-start markers exist as executable encodings in the toolchain
 *   and are accepted by the emulator front-end.
 *
 * NOTE:
 * This suite does not attempt to execute full SIMT/vector bodies. It validates the
 * "block boundary marker" contract for the typed block-start instructions that
 * participate in the v0.3 strict contract.
 */

#include "linx_test.h"

static void test_typed_block_starts_smoke(void)
{
    /*
     * Each BSTART.<type> terminates the current block and begins the next block.
     * We close each empty typed block by starting a new fall-through STD block
     * using C.BSTART. This ensures subsequent C code is still within a block.
     */
    __asm__ volatile(
        "BSTART.MSEQ 0\n"
        "C.BSTART\n"
        "BSTART.MPAR 0\n"
        "C.BSTART\n"
        "BSTART.VPAR 0\n"
        "C.BSTART\n"
        "BSTART.VSEQ 0\n"
        "C.BSTART\n"
        :
        :
        : "memory");
}

void run_v03_vector_tile_tests(void)
{
    test_start(0x1200);
    uart_puts("v0.3 typed BSTART.* smoke ... ");

    test_typed_block_starts_smoke();

    test_pass();
}
