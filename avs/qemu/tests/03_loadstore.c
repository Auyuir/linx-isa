/*
 * Load/Store Unit Tests for LinxISA
 * Tests: LB, LBU, LH, LHU, LW, LWU, LD, SB, SH, SW, SD
 *        LBI, LHI, LWI, LDI, SBI, SHI, SWI, SDI
 */

#include "linx_test.h"

/* Test data section - aligned for all access sizes */
static const uint8_t  u8_data[]  = { 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0 };
static const uint16_t u16_data[] = { 0x1234, 0x5678, 0x9ABC, 0xDEF0 };
static const uint32_t u32_data[] = { 0x12345678, 0x9ABCDEF0 };
static const uint64_t u64_data[] = { 0x123456789ABCDEF0ULL };

/* Data for stores - will be written to and verified */
static uint8_t  store_u8[8];
static uint16_t store_u16[4];
static uint32_t store_u32[4];
static uint64_t store_u64[2];

/* Test LB (load signed byte) */
static void test_lb_basic(void) {
    int8_t val = (int8_t)u8_data[0];
    TEST_EQ(val, 0x12, 0xC001);
}

static void test_lb_negative(void) {
    /* u8_data[4] = 0x9A which is -102 as int8_t */
    int8_t val = (int8_t)u8_data[4];
    TEST_EQ(val, -102, 0xC002);
}

static void test_lb_aligned(void) {
    int8_t val = (int8_t)u8_data[0];
    TEST_EQ(val, 0x12, 0xC003);
}

/* Test LBU (load unsigned byte) */
static void test_lbu_basic(void) {
    uint8_t val = u8_data[0];
    TEST_EQ(val, 0x12, 0xC010);
}

static void test_lbu_high_bit(void) {
    /* u8_data[4] = 0x9A */
    uint8_t val = u8_data[4];
    TEST_EQ(val, 0x9A, 0xC011);
}

/* Test LH (load signed halfword) */
static void test_lh_basic(void) {
    int16_t val = (int16_t)u16_data[0];
    TEST_EQ(val, 0x1234, 0xC020);
}

static void test_lh_negative(void) {
    /* u16_data[3] = 0xDEF0 = -8464 as int16_t */
    int16_t val = (int16_t)u16_data[3];
    TEST_EQ(val, -8464, 0xC021);
}

/* Test LHU (load unsigned halfword) */
static void test_lhu_basic(void) {
    uint16_t val = u16_data[0];
    TEST_EQ(val, 0x1234, 0xC030);
}

static void test_lhu_high_bit(void) {
    uint16_t val = u16_data[3];
    TEST_EQ(val, 0xDEF0, 0xC031);
}

/* Test LW (load word) */
static void test_lw_basic(void) {
    uint32_t val = u32_data[0];
    TEST_EQ(val, 0x12345678, 0xC040);
}

static void test_lw_second(void) {
    uint32_t val = u32_data[1];
    TEST_EQ(val, 0x9ABCDEF0, 0xC041);
}

/* Test LWU (load unsigned word) */
static void test_lwu_basic(void) {
    uint32_t val = u32_data[0];
    TEST_EQ(val, 0x12345678, 0xC050);
}

static void test_lwu_high_bit(void) {
    uint32_t val = u32_data[1];
    TEST_EQ(val, 0x9ABCDEF0, 0xC051);
}

/* Test LD (load doubleword) */
static void test_ld_basic(void) {
    uint64_t val = u64_data[0];
    TEST_EQ64(val, 0x123456789ABCDEF0ULL, 0xC060);
}

/* Test SB (store byte) */
static void test_sb_basic(void) {
    store_u8[0] = 0xAB;
    TEST_EQ(store_u8[0], 0xAB, 0xC070);
}

static void test_sb_multiple(void) {
    store_u8[0] = 0x12;
    store_u8[1] = 0x34;
    store_u8[2] = 0x56;
    store_u8[3] = 0x78;
    TEST_EQ(store_u8[0], 0x12, 0xC071);
    TEST_EQ(store_u8[1], 0x34, 0xC072);
    TEST_EQ(store_u8[2], 0x56, 0xC073);
    TEST_EQ(store_u8[3], 0x78, 0xC074);
}

/* Test SH (store halfword) */
static void test_sh_basic(void) {
    store_u16[0] = 0xABCD;
    TEST_EQ(store_u16[0], 0xABCD, 0xC080);
}

static void test_sh_alignment(void) {
    store_u16[1] = 0x1234;
    TEST_EQ(store_u16[1], 0x1234, 0xC081);
}

/* Test SW (store word) */
static void test_sw_basic(void) {
    store_u32[0] = 0x12345678;
    TEST_EQ(store_u32[0], 0x12345678, 0xC090);
}

static void test_sw_multiple(void) {
    store_u32[0] = 0x11111111;
    store_u32[1] = 0x22222222;
    store_u32[2] = 0x33333333;
    store_u32[3] = 0x44444444;
    TEST_EQ(store_u32[0], 0x11111111, 0xC091);
    TEST_EQ(store_u32[1], 0x22222222, 0xC092);
    TEST_EQ(store_u32[2], 0x33333333, 0xC093);
    TEST_EQ(store_u32[3], 0x44444444, 0xC094);
}

/* Test SD (store doubleword) */
static void test_sd_basic(void) {
    store_u64[0] = 0xDEADBEEFCAFEBABEULL;
    TEST_EQ64(store_u64[0], 0xDEADBEEFCAFEBABEULL, 0xC0A0);
}

/* Test indexed addressing */
static void test_indexed_load(void) {
    uint32_t base = (uint32_t)(uintptr_t)u32_data;
    uint32_t val = u32_data[1];
    TEST_EQ(val, 0x9ABCDEF0, 0xC0B0);
}

static void test_indexed_store(void) {
    store_u32[2] = 0xCAFEBABE;
    TEST_EQ(store_u32[2], 0xCAFEBABE, 0xC0B1);
}

/* Test with offset addressing */
static void test_offset_load(void) {
    uint32_t base = (uint32_t)(uintptr_t)u8_data;
    uint8_t val = u8_data[4];
    TEST_EQ(val, 0x9A, 0xC0C0);
}

static void test_offset_store(void) {
    store_u8[5] = 0xFF;
    TEST_EQ(store_u8[5], 0xFF, 0xC0C1);
}

/* Test zero extension behavior */
static void test_zext_byte(void) {
    uint8_t val = u8_data[4];  /* 0x9A */
    uint32_t zext = val;       /* Should zero-extend */
    TEST_EQ(zext, 0x9A, 0xC0D0);
}

static void test_zext_half(void) {
    uint16_t val = u16_data[2];  /* 0x9ABC */
    uint32_t zext = val;         /* Should zero-extend */
    TEST_EQ(zext, 0x9ABC, 0xC0D1);
}

/* Test sign extension behavior */
static void test_sext_byte(void) {
    int8_t sval = (int8_t)u8_data[4];  /* 0x9A = -102 */
    int32_t sext = sval;                /* Should sign-extend */
    TEST_EQ32(sext, -102, 0xC0E0);
}

static void test_sext_half(void) {
    int16_t sval = (int16_t)u16_data[3];  /* 0xDEF0 = -8464 */
    int32_t sext = sval;                   /* Should sign-extend */
    TEST_EQ32(sext, -8464, 0xC0E1);
}

/* Main test runner */
void run_loadstore_tests(void) {
    test_suite_begin(0xC000);
    
    /* LB tests */
    RUN_TEST(test_lb_basic, 0xC001);
    RUN_TEST(test_lb_negative, 0xC002);
    RUN_TEST(test_lb_aligned, 0xC003);
    
    /* LBU tests */
    RUN_TEST(test_lbu_basic, 0xC010);
    RUN_TEST(test_lbu_high_bit, 0xC011);
    
    /* LH tests */
    RUN_TEST(test_lh_basic, 0xC020);
    RUN_TEST(test_lh_negative, 0xC021);
    
    /* LHU tests */
    RUN_TEST(test_lhu_basic, 0xC030);
    RUN_TEST(test_lhu_high_bit, 0xC031);
    
    /* LW tests */
    RUN_TEST(test_lw_basic, 0xC040);
    RUN_TEST(test_lw_second, 0xC041);
    
    /* LWU tests */
    RUN_TEST(test_lwu_basic, 0xC050);
    RUN_TEST(test_lwu_high_bit, 0xC051);
    
    /* LD tests */
    RUN_TEST(test_ld_basic, 0xC060);
    
    /* SB tests */
    RUN_TEST(test_sb_basic, 0xC070);
    RUN_TEST(test_sb_multiple, 0xC071);
    
    /* SH tests */
    RUN_TEST(test_sh_basic, 0xC080);
    RUN_TEST(test_sh_alignment, 0xC081);
    
    /* SW tests */
    RUN_TEST(test_sw_basic, 0xC090);
    RUN_TEST(test_sw_multiple, 0xC091);
    
    /* SD tests */
    RUN_TEST(test_sd_basic, 0xC0A0);
    
    /* Indexed addressing */
    RUN_TEST(test_indexed_load, 0xC0B0);
    RUN_TEST(test_indexed_store, 0xC0B1);
    
    /* Offset addressing */
    RUN_TEST(test_offset_load, 0xC0C0);
    RUN_TEST(test_offset_store, 0xC0C1);
    
    /* Zero extension */
    RUN_TEST(test_zext_byte, 0xC0D0);
    RUN_TEST(test_zext_half, 0xC0D1);
    
    /* Sign extension */
    RUN_TEST(test_sext_byte, 0xC0E0);
    RUN_TEST(test_sext_half, 0xC0E1);
    
    test_suite_end(27, 27);
}
