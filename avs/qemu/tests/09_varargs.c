/*
 * Varargs ABI Unit Tests for LinxISA
 *
 * These tests validate that:
 * - va_start points at the first variadic slot
 * - va_arg advances with correct size/alignment
 * - i32 and i64 values are retrieved correctly under -O2
 *
 * LinxISA currently uses a simple `void*` va_list in Clang. The LinxISA
 * calling convention must therefore pass varargs in memory with natural
 * size/alignment.
 */

#include "linx_test.h"

#include <stdarg.h>
#include <stdint.h>

__attribute__((noinline)) static int64_t sum_i32(int n, ...) {
    va_list ap;
    va_start(ap, n);
    int64_t acc = 0;
    for (int i = 0; i < n; i++) {
        acc += (int64_t)va_arg(ap, int);
    }
    va_end(ap);
    return acc;
}

__attribute__((noinline)) static int64_t sum_i64(int n, ...) {
    va_list ap;
    va_start(ap, n);
    int64_t acc = 0;
    for (int i = 0; i < n; i++) {
        acc += (int64_t)va_arg(ap, long long);
    }
    va_end(ap);
    return acc;
}

__attribute__((noinline)) static int64_t mixed_i32_i64(int fixed, ...) {
    /* Dummy fixed arg so that varargs don't start at offset 0. */
    (void)fixed;

    va_list ap;
    va_start(ap, fixed);

    int a = va_arg(ap, int);
    long long b = va_arg(ap, long long);
    int c = va_arg(ap, int);
    long long d = va_arg(ap, long long);

    va_end(ap);
    return (int64_t)a + (int64_t)b + (int64_t)c + (int64_t)d;
}

__attribute__((noinline)) static int64_t sum_i32_via_va_list(int tag, va_list ap) {
    (void)tag;
    int a = va_arg(ap, int);
    int b = va_arg(ap, int);
    int c = va_arg(ap, int);
    return (int64_t)a + (int64_t)b + (int64_t)c;
}

__attribute__((noinline)) static int64_t sum_i32_pass_va_list(int tag, ...) {
    va_list ap;
    va_start(ap, tag);
    int64_t r = sum_i32_via_va_list(tag, ap);
    va_end(ap);
    return r;
}

static void test_varargs_i32_sum(void) {
    int64_t r = sum_i32(6, 1, 2, 3, 4, 5, 6);
    TEST_EQ64(r, 21, 0x9001);
}

static void test_varargs_i64_sum(void) {
    int64_t r = sum_i64(4, 10000000000LL, 2LL, -3LL, 4LL);
    TEST_EQ64(r, 10000000003LL, 0x9002);
}

static void test_varargs_alignment_mixed(void) {
    /* i32, i64, i32, i64 */
    int64_t r = mixed_i32_i64(123, 7, 0x1122334455667788LL, -9, -5LL);
    TEST_EQ64(r, (int64_t)7 + (int64_t)0x1122334455667788LL - 9 - 5, 0x9003);
}

static void test_varargs_pass_va_list(void) {
    /* Ensure passing va_list to another function works under -O2. */
    int64_t r = sum_i32_pass_va_list(42, 10, 20, -3);
    TEST_EQ64(r, 27, 0x9004);
}

void run_varargs_tests(void) {
    test_suite_begin(0x9000);
    RUN_TEST(test_varargs_i32_sum, 0x9001);
    RUN_TEST(test_varargs_i64_sum, 0x9002);
    RUN_TEST(test_varargs_alignment_mixed, 0x9003);
    RUN_TEST(test_varargs_pass_va_list, 0x9004);
    test_suite_end(4, 4);
}
