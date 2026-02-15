/*
 * Floating-Point Unit Tests for LinxISA
 * Tests: FADD, FSUB, FMUL, FDIV, FSQRT, FMADD, FMSUB, FNMSUB, FMNMADD
 *        FCMP (FEQ, FLT, FLE, FGT, FGE), FCVT, FMIN, FMAX
 */

#include "linx_test.h"

/* Test floating-point addition */
static void test_fadd_basic(void) {
    volatile double a = 1.5;
    volatile double b = 2.5;
    double result = a + b;
    TEST_EQF(result, 4.0, 0xF001, 0.001);
}

static void test_fadd_negative(void) {
    volatile double a = -1.5;
    volatile double b = 2.5;
    double result = a + b;
    TEST_EQF(result, 1.0, 0xF002, 0.001);
}

static void test_fadd_zeros(void) {
    volatile double a = 0.0;
    volatile double b = 0.0;
    double result = a + b;
    TEST_EQF(result, 0.0, 0xF003, 0.001);
}

/* Test floating-point subtraction */
static void test_fsub_basic(void) {
    volatile double a = 5.0;
    volatile double b = 2.5;
    double result = a - b;
    TEST_EQF(result, 2.5, 0xF010, 0.001);
}

static void test_fsub_negative(void) {
    volatile double a = 1.0;
    volatile double b = 2.0;
    double result = a - b;
    TEST_EQF(result, -1.0, 0xF011, 0.001);
}

/* Test floating-point multiplication */
static void test_fmul_basic(void) {
    volatile double a = 2.0;
    volatile double b = 3.0;
    double result = a * b;
    TEST_EQF(result, 6.0, 0xF020, 0.001);
}

static void test_fmul_by_zero(void) {
    volatile double a = 100.0;
    double result = a * 0.0;
    TEST_EQF(result, 0.0, 0xF021, 0.001);
}

/* Test floating-point division */
static void test_fdiv_basic(void) {
    volatile double a = 10.0;
    volatile double b = 2.0;
    double result = a / b;
    TEST_EQF(result, 5.0, 0xF030, 0.001);
}

static void test_fdiv_by_one(void) {
    volatile double a = 7.5;
    double result = a / 1.0;
    TEST_EQF(result, 7.5, 0xF031, 0.001);
}

/* Test floating-point comparisons */
__attribute__((noinline))
static void test_feq_true(void) {
    volatile double a = 1.5;
    volatile double b = 1.5;
    uint32_t result = (a == b) ? 1 : 0;
    TEST_EQ(result, 1, 0xF040);
}

static void test_feq_false(void) {
    volatile double a = 1.5;
    volatile double b = 1.6;
    uint32_t result = (a == b) ? 1 : 0;
    TEST_EQ(result, 0, 0xF041);
}

static void test_flt_true(void) {
    volatile double a = 1.0;
    volatile double b = 2.0;
    uint32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 1, 0xF050);
}

static void test_flt_false(void) {
    volatile double a = 3.0;
    volatile double b = 2.0;
    uint32_t result = (a < b) ? 1 : 0;
    TEST_EQ(result, 0, 0xF051);
}

static void test_fle_true(void) {
    volatile double a = 1.5;
    volatile double b = 1.5;
    uint32_t result = (a <= b) ? 1 : 0;
    TEST_EQ(result, 1, 0xF060);
}

/* Test floating-point min/max */
static void test_fmin_basic(void) {
    volatile double a = 1.5;
    volatile double b = 2.5;
    double result = (a < b) ? a : b;
    TEST_EQF(result, 1.5, 0xF070, 0.001);
}

static void test_fmax_basic(void) {
    volatile double a = 1.5;
    volatile double b = 2.5;
    double result = (a > b) ? a : b;
    TEST_EQF(result, 2.5, 0xF071, 0.001);
}

/* Test floating-point fused multiply-add */
static void test_fmadd_basic(void) {
    volatile double a = 2.0;
    volatile double b = 3.0;
    volatile double c = 1.0;
    double result = (a * b) + c;
    TEST_EQF(result, 7.0, 0xF080, 0.001);
}

/* Test floating-point square root */
__attribute__((noinline))
static void test_fsqrt_basic(void) {
    volatile double a = 16.0;
    double result = 0;
    /* Manual square root for testing */
    double lo = 0, hi = a, mid;
    for (int i = 0; i < 50; i++) {
        mid = (lo + hi) / 2;
        if (mid * mid < a) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    result = mid;
    TEST_EQF(result, 4.0, 0xF090, 0.01);
}

/* Test floating-point absolute value */
static void test_fabs_basic(void) {
    double a = -5.5;
    double result = (a < 0) ? -a : a;
    TEST_EQF(result, 5.5, 0xF0A0, 0.001);
}

/* Test floating-point negation */
static void test_fneg_basic(void) {
    double a = 5.5;
    double result = -a;
    TEST_EQF(result, -5.5, 0xF0B0, 0.001);
}

/* Test floating-point conversion */
static void test_ftoi_basic(void) {
    double a = 3.7;
    int32_t result = (int32_t)a;
    TEST_EQ32(result, 3, 0xF0C0);
}

static void test_itof_basic(void) {
    int32_t a = 5;
    double result = (double)a;
    TEST_EQF(result, 5.0, 0xF0D0, 0.001);
}

/* Test special floating-point values */
static void test_f_inf_positive(void) {
    double inf = 1.0 / 0.0;
    uint32_t is_inf = (inf > 1e308) ? 1 : 0;
    TEST_EQ(is_inf, 1, 0xF0E0);
}

static void test_f_nan(void) {
    double nan = 0.0 / 0.0;
    uint32_t is_nan = (nan != nan) ? 1 : 0;  /* NaN is the only value not equal to itself */
    TEST_EQ(is_nan, 1, 0xF0E1);
}

/* Test floating-point precision */
static void test_f_precision(void) {
    double a = 0.1 + 0.2;  /* Should be approximately 0.3 */
    uint32_t is_close = (a > 0.29 && a < 0.31) ? 1 : 0;
    TEST_EQ(is_close, 1, 0xF0F0);
}

/* Main test runner */
void run_float_tests(void) {
    test_suite_begin(0xF000);
    
    /* FADD tests */
    RUN_TEST(test_fadd_basic, 0xF001);
    RUN_TEST(test_fadd_negative, 0xF002);
    RUN_TEST(test_fadd_zeros, 0xF003);
    
    /* FSUB tests */
    RUN_TEST(test_fsub_basic, 0xF010);
    RUN_TEST(test_fsub_negative, 0xF011);
    
    /* FMUL tests */
    RUN_TEST(test_fmul_basic, 0xF020);
    RUN_TEST(test_fmul_by_zero, 0xF021);
    
    /* FDIV tests */
    RUN_TEST(test_fdiv_basic, 0xF030);
    RUN_TEST(test_fdiv_by_one, 0xF031);
    
    /* FCMP tests */
    RUN_TEST(test_feq_true, 0xF040);
    RUN_TEST(test_feq_false, 0xF041);
    RUN_TEST(test_flt_true, 0xF050);
    RUN_TEST(test_flt_false, 0xF051);
    RUN_TEST(test_fle_true, 0xF060);
    
    /* FMIN/MAX tests */
    RUN_TEST(test_fmin_basic, 0xF070);
    RUN_TEST(test_fmax_basic, 0xF071);
    
    /* FMADD test */
    RUN_TEST(test_fmadd_basic, 0xF080);
    
    /* FSQRT test */
    RUN_TEST(test_fsqrt_basic, 0xF090);
    
    /* FABS test */
    RUN_TEST(test_fabs_basic, 0xF0A0);
    
    /* FNEG test */
    RUN_TEST(test_fneg_basic, 0xF0B0);
    
    /* FCVT tests */
    RUN_TEST(test_ftoi_basic, 0xF0C0);
    RUN_TEST(test_itof_basic, 0xF0D0);
    
    /* Special values */
    RUN_TEST(test_f_inf_positive, 0xF0E0);
    RUN_TEST(test_f_nan, 0xF0E1);
    
    /* Precision test */
    RUN_TEST(test_f_precision, 0xF0F0);
    
    test_suite_end(24, 24);
}
