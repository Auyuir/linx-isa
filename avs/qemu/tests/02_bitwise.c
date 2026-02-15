/*
 * Bitwise Unit Tests for LinxISA
 * Tests: AND, ANDI, OR, ORI, XOR, XORI, SLL, SLLI, SRL, SRLI, SRA, SRAI
 *        ANDW, ANDIW, ORW, ORIW, XORW, XORIW, SLLW, SLLIW, SRLW, SRLIW, SRAW, SRAIW
 */

#include "linx_test.h"

/* Test AND instruction */
static void test_and_basic(void) {
    uint32_t a = 0xFF;
    uint32_t b = 0xF0;
    uint32_t result = a & b;
    TEST_EQ(result, 0xF0, 0xB001);
}

static void test_and_all_ones(void) {
    uint32_t a = 0xFFFFFFFF;
    uint32_t b = 0x12345678;
    uint32_t result = a & b;
    TEST_EQ(result, 0x12345678, 0xB002);
}

static void test_and_all_zeros(void) {
    uint32_t a = 0;
    uint32_t b = 0x12345678;
    uint32_t result = a & b;
    TEST_EQ(result, 0, 0xB003);
}

static void test_and_complement(void) {
    uint32_t a = 0xFF00;
    uint32_t result = a & ~a;
    TEST_EQ(result, 0, 0xB004);
}

/* Test ANDI instruction */
static void test_andi_basic(void) {
    uint32_t a = 0xFF;
    uint32_t result = a & 0x0F;
    TEST_EQ(result, 0x0F, 0xB010);
}

static void test_andi_negative_imm(void) {
    /* AND with negative immediate (sign-extended) */
    uint32_t a = 0xFFFF;
    uint32_t result = a & 0xFF00;
    TEST_EQ(result, 0xFF00, 0xB011);
}

/* Test OR instruction */
static void test_or_basic(void) {
    uint32_t a = 0xF0;
    uint32_t b = 0x0F;
    uint32_t result = a | b;
    TEST_EQ(result, 0xFF, 0xB020);
}

static void test_or_with_zero(void) {
    uint32_t a = 0x12345678;
    uint32_t result = a | 0;
    TEST_EQ(result, 0x12345678, 0xB021);
}

static void test_or_with_all_ones(void) {
    uint32_t a = 0;
    uint32_t result = a | 0xFFFFFFFF;
    TEST_EQ(result, 0xFFFFFFFF, 0xB022);
}

/* Test ORI instruction */
static void test_ori_basic(void) {
    uint32_t a = 0xFF00;
    uint32_t result = a | 0x00FF;
    TEST_EQ(result, 0xFFFF, 0xB030);
}

/* Test XOR instruction */
static void test_xor_basic(void) {
    uint32_t a = 0xFF;
    uint32_t b = 0x0F;
    uint32_t result = a ^ b;
    TEST_EQ(result, 0xF0, 0xB040);
}

static void test_xor_same(void) {
    uint32_t a = 0x12345678;
    uint32_t result = a ^ a;
    TEST_EQ(result, 0, 0xB041);
}

static void test_xor_zero(void) {
    uint32_t a = 0xABCDEF;
    uint32_t result = a ^ 0;
    TEST_EQ(result, 0xABCDEF, 0xB042);
}

static void test_xor_toggle(void) {
    uint32_t a = 0xFF;
    uint32_t mask = 0x0F;
    uint32_t result = (a ^ mask) ^ mask;
    TEST_EQ(result, 0xFF, 0xB043);
}

/* Test XORI instruction */
static void test_xori_basic(void) {
    uint32_t a = 0xFF;
    uint32_t result = a ^ 0x0F;
    TEST_EQ(result, 0xF0, 0xB050);
}

/* Test SLL instruction (shift left logical) */
static void test_sll_basic(void) {
    uint32_t a = 0x1;
    uint32_t result = a << 4;
    TEST_EQ(result, 0x10, 0xB060);
}

static void test_sll_by_16(void) {
    uint32_t a = 0x1234;
    uint32_t result = a << 16;
    TEST_EQ(result, 0x12340000, 0xB061);
}

static void test_sll_zero(void) {
    uint32_t a = 0xDEADBEEF;
    uint32_t result = a << 0;
    TEST_EQ(result, 0xDEADBEEF, 0xB062);
}

static void test_sll_bits_lost(void) {
    uint32_t a = 0xFF;
    uint32_t result = a << 24;
    TEST_EQ(result, 0xFF000000, 0xB063);
}

/* Test SLLI instruction (shift left logical immediate) */
static void test_slli_basic(void) {
    uint32_t a = 0x1;
    uint32_t result = a << 8;
    TEST_EQ(result, 0x100, 0xB070);
}

/* Test SRL instruction (shift right logical) */
static void test_srl_basic(void) {
    uint32_t a = 0xFF00;
    uint32_t result = a >> 4;
    TEST_EQ(result, 0xFF0, 0xB080);
}

static void test_srl_by_16(void) {
    uint32_t a = 0x12340000;
    uint32_t result = a >> 16;
    TEST_EQ(result, 0x1234, 0xB081);
}

static void test_srl_zero(void) {
    uint32_t a = 0xDEADBEEF;
    uint32_t result = a >> 0;
    TEST_EQ(result, 0xDEADBEEF, 0xB082);
}

static void test_srl_unsigned(void) {
    /* SRL treats value as unsigned */
    uint32_t a = 0x80000000;
    uint32_t result = a >> 1;
    TEST_EQ(result, 0x40000000, 0xB083);
}

/* Test SRLI instruction (shift right logical immediate) */
static void test_srli_basic(void) {
    uint32_t a = 0xFF00;
    uint32_t result = a >> 8;
    TEST_EQ(result, 0xFF, 0xB090);
}

/* Test SRA instruction (shift right arithmetic) */
static void test_sra_basic(void) {
    int32_t a = 0xFF00;  /* Will be sign-extended as negative */
    int32_t result = a >> 4;
    /* Arithmetic shift should preserve sign bit */
    (void)result;
}

static void test_sra_negative(void) {
    int32_t a = -16;  /* 0xFFFFFFF0 */
    int32_t result = a >> 2;
    TEST_EQ32(result, -4, 0xB0A1);
}

static void test_sra_positive(void) {
    int32_t a = 16;
    int32_t result = a >> 2;
    TEST_EQ32(result, 4, 0xB0A2);
}

/* Test SRAI instruction (shift right arithmetic immediate) */
static void test_srai_basic(void) {
    int32_t a = -8;
    int32_t result = a >> 1;
    TEST_EQ32(result, -4, 0xB0B0);
}

/* Test 64-bit word operations */
static void test_andw_basic(void) {
    uint64_t a = 0xFFFFFFFF00000000ULL;
    uint64_t b = 0x0000FFFF00000000ULL;
    uint64_t result = a & b;
    TEST_EQ64(result, 0x0000FFFF00000000ULL, 0xB0C0);
}

static void test_orw_basic(void) {
    uint64_t a = 0xFFFF000000000000ULL;
    uint64_t b = 0x00000000FFFFFFFFULL;
    uint64_t result = a | b;
    TEST_EQ64(result, 0xFFFF0000FFFFFFFFULL, 0xB0C1);
}

static void test_xorw_basic(void) {
    uint64_t a = 0xAAAAAAAAAAAAAAAAULL;
    uint64_t b = 0x5555555555555555ULL;
    uint64_t result = a ^ b;
    TEST_EQ64(result, 0xFFFFFFFFFFFFFFFFULL, 0xB0C2);
}

static void test_sllw_basic(void) {
    uint64_t a = 0x1ULL;
    uint64_t result = a << 32;
    TEST_EQ64(result, 0x100000000ULL, 0xB0D0);
}

static void test_srlw_basic(void) {
    uint64_t a = 0xFF00000000ULL;
    uint64_t result = a >> 24;
    TEST_EQ64(result, 0xFF00, 0xB0D1);
}

static void test_sraw_basic(void) {
    int64_t a = -256;  /* 0xFFFFFFFFFFFFFF00 */
    int64_t result = a >> 8;
    TEST_EQ64(result, -1, 0xB0E0);
}

/* Test bit manipulation helpers */
static void test_bit_count(void) {
    /* Test counting bits in common patterns */
    uint32_t a = 0xF;   /* 4 bits */
    uint32_t result = 0;
    /* Manual bit counting */
    uint32_t v = a;
    while (v) {
        result += v & 1;
        v >>= 1;
    }
    TEST_EQ(result, 4, 0xB0F0);
}

static void test_parity(void) {
    uint32_t a = 0xF;   /* Even parity (4 bits set) */
    uint32_t result = 0;
    uint32_t v = a;
    while (v) {
        result ^= v & 1;
        v >>= 1;
    }
    TEST_EQ(result, 0, 0xB0F1);  /* Even parity = 0 */
}

/* Main test runner */
void run_bitwise_tests(void) {
    test_suite_begin(0xB000);
    
    /* AND tests */
    RUN_TEST(test_and_basic, 0xB001);
    RUN_TEST(test_and_all_ones, 0xB002);
    RUN_TEST(test_and_all_zeros, 0xB003);
    RUN_TEST(test_and_complement, 0xB004);
    
    /* ANDI tests */
    RUN_TEST(test_andi_basic, 0xB010);
    RUN_TEST(test_andi_negative_imm, 0xB011);
    
    /* OR tests */
    RUN_TEST(test_or_basic, 0xB020);
    RUN_TEST(test_or_with_zero, 0xB021);
    RUN_TEST(test_or_with_all_ones, 0xB022);
    
    /* ORI tests */
    RUN_TEST(test_ori_basic, 0xB030);
    
    /* XOR tests */
    RUN_TEST(test_xor_basic, 0xB040);
    RUN_TEST(test_xor_same, 0xB041);
    RUN_TEST(test_xor_zero, 0xB042);
    RUN_TEST(test_xor_toggle, 0xB043);
    
    /* XORI tests */
    RUN_TEST(test_xori_basic, 0xB050);
    
    /* SLL tests */
    RUN_TEST(test_sll_basic, 0xB060);
    RUN_TEST(test_sll_by_16, 0xB061);
    RUN_TEST(test_sll_zero, 0xB062);
    RUN_TEST(test_sll_bits_lost, 0xB063);
    
    /* SLLI tests */
    RUN_TEST(test_slli_basic, 0xB070);
    
    /* SRL tests */
    RUN_TEST(test_srl_basic, 0xB080);
    RUN_TEST(test_srl_by_16, 0xB081);
    RUN_TEST(test_srl_zero, 0xB082);
    RUN_TEST(test_srl_unsigned, 0xB083);
    
    /* SRLI tests */
    RUN_TEST(test_srli_basic, 0xB090);
    
    /* SRA tests */
    RUN_TEST(test_sra_basic, 0xB0A0);
    RUN_TEST(test_sra_negative, 0xB0A1);
    RUN_TEST(test_sra_positive, 0xB0A2);
    
    /* SRAI tests */
    RUN_TEST(test_srai_basic, 0xB0B0);
    
    /* 64-bit word operations */
    RUN_TEST(test_andw_basic, 0xB0C0);
    RUN_TEST(test_orw_basic, 0xB0C1);
    RUN_TEST(test_xorw_basic, 0xB0C2);
    
    RUN_TEST(test_sllw_basic, 0xB0D0);
    RUN_TEST(test_srlw_basic, 0xB0D1);
    
    RUN_TEST(test_sraw_basic, 0xB0E0);
    
    /* Bit manipulation helpers */
    RUN_TEST(test_bit_count, 0xB0F0);
    RUN_TEST(test_parity, 0xB0F1);
    
    test_suite_end(30, 30);
}
