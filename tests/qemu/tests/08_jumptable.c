/*
 * Jump Table / Indirect Branch Unit Tests for LinxISA
 *
 * Purpose:
 * - Exercise compiler-generated jump tables (switch lowering) which require:
 *   - JumpTable address materialization + data relocations
 *   - Indirect branch lowering (BRIND/JR) + BlockISA IND blocks (SETC.TGT)
 *
 * Note: qemu-tests defaults to -fno-jump-tables; run_tests.py removes it for
 * this source file.
 */

#include "linx_test.h"

__attribute__((noinline)) static int dense_switch(int x) {
    /* Keep cases dense so Clang prefers a jump table at -O2. */
    switch (x) {
    case 0:  return 11;
    case 1:  return 22;
    case 2:  return 33;
    case 3:  return 44;
    case 4:  return 55;
    case 5:  return 66;
    case 6:  return 77;
    case 7:  return 88;
    case 8:  return 99;
    case 9:  return 111;
    case 10: return 122;
    case 11: return 133;
    case 12: return 144;
    case 13: return 155;
    case 14: return 166;
    case 15: return 177;
    default: return -1;
    }
}

static void test_jumptable_dense_cases(void) {
    static const int expect[16] = {
        11, 22, 33, 44, 55, 66, 77, 88, 99, 111, 122, 133, 144, 155, 166, 177,
    };
    for (int i = 0; i < 16; i++) {
        int got = dense_switch(i);
        TEST_EQ32(got, expect[i], 0x8001);
    }
}

static void test_jumptable_default(void) {
    TEST_EQ32(dense_switch(-1), -1, 0x8002);
    TEST_EQ32(dense_switch(16), -1, 0x8003);
    TEST_EQ32(dense_switch(1234), -1, 0x8004);
}

void run_jumptable_tests(void) {
    test_suite_begin(0x8000);
    RUN_TEST(test_jumptable_dense_cases, 0x8001);
    RUN_TEST(test_jumptable_default, 0x8002);
    test_suite_end(2, 2);
}

