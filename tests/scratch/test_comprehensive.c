/* Comprehensive test for LinxISA instructions */

/* Define integer types for bare-metal */
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed short int16_t;
typedef unsigned short uint16_t;
typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef signed long long int64_t;
typedef unsigned long long uint64_t;

/* Helper to write a value to output memory */
static inline void write_result(int value) {
    volatile int *output = (volatile int *)0x100;
    *output = value;
}

/* Test arithmetic operations */
static int test_arithmetic(void) {
    int result = 0;
    
    volatile int a = 42;
    volatile int b = 13;
    
    /* ADD */
    if (a + b == 55) result |= 1;
    
    /* SUB */
    if (a - b == 29) result |= 2;
    
    /* MUL */
    if (a * b == 546) result |= 4;
    
    /* DIV */
    if (a / b == 3) result |= 8;
    
    /* REM */
    if (a % b == 3) result |= 16;
    
    return result;  /* Should be 31 */
}

/* Test logical operations */
static int test_logical(void) {
    int result = 0;
    
    volatile uint64_t x = 0xFF00FF00FF00FF00ULL;
    volatile uint64_t y = 0x00FF00FF00FF00FFULL;
    
    /* AND */
    if ((x & y) == 0) result |= 1;
    
    /* OR */
    if ((x | y) == 0xFFFFFFFFFFFFFFFFULL) result |= 2;
    
    /* XOR */
    if ((x ^ y) == 0xFFFFFFFFFFFFFFFFULL) result |= 4;
    
    return result;  /* Should be 7 */
}

/* Test shift operations */
static int test_shifts(void) {
    int result = 0;
    
    volatile uint64_t val = 1;
    
    /* SLL (shift left) */
    if ((val << 10) == 1024) result |= 1;
    
    /* SRL (shift right logical) */
    volatile uint64_t high = 0x8000000000000000ULL;
    if ((high >> 63) == 1) result |= 2;
    
    /* SRA (shift right arithmetic) */
    volatile int64_t neg = -16;
    if ((neg >> 2) == -4) result |= 4;
    
    return result;  /* Should be 7 */
}

/* Test comparison operations */
static int test_comparisons(void) {
    int result = 0;
    
    volatile int a = 10;
    volatile int b = 20;
    volatile int c = -5;
    
    /* EQ */
    if (a == a) result |= 1;
    
    /* NE */
    if (a != b) result |= 2;
    
    /* LT signed */
    if (c < a) result |= 4;
    
    /* GE signed */
    if (a >= c) result |= 8;
    
    /* LTU unsigned */
    volatile unsigned int ua = 10;
    volatile unsigned int ub = 4000000000U;
    if (ua < ub) result |= 16;
    
    return result;  /* Should be 31 */
}

/* Test memory operations */
static int test_memory(void) {
    int result = 0;
    
    volatile uint8_t *p8 = (volatile uint8_t *)0x200;
    volatile uint16_t *p16 = (volatile uint16_t *)0x210;
    volatile uint32_t *p32 = (volatile uint32_t *)0x220;
    volatile uint64_t *p64 = (volatile uint64_t *)0x230;
    
    /* Store and load byte */
    *p8 = 0xAB;
    if (*p8 == 0xAB) result |= 1;
    
    /* Store and load halfword */
    *p16 = 0xCDEF;
    if (*p16 == 0xCDEF) result |= 2;
    
    /* Store and load word */
    *p32 = 0x12345678;
    if (*p32 == 0x12345678) result |= 4;
    
    /* Store and load doubleword */
    *p64 = 0xFEDCBA9876543210ULL;
    if (*p64 == 0xFEDCBA9876543210ULL) result |= 8;
    
    return result;  /* Should be 15 */
}

/* Test loops and branching */
static int test_loops(void) {
    int result = 0;
    
    /* Simple for loop */
    volatile int sum = 0;
    for (int i = 1; i <= 10; i++) {
        sum += i;
    }
    if (sum == 55) result |= 1;
    
    /* While loop */
    volatile int count = 0;
    volatile int n = 5;
    while (n > 0) {
        count++;
        n--;
    }
    if (count == 5) result |= 2;
    
    /* Nested loops */
    volatile int product = 0;
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 4; j++) {
            product++;
        }
    }
    if (product == 12) result |= 4;
    
    return result;  /* Should be 7 */
}

__attribute__((noreturn))
void _start(void) {
    int total_result = 0;
    int test_num = 0;
    
    /* Run arithmetic tests */
    int arith = test_arithmetic();
    if (arith == 31) total_result |= (1 << test_num);
    test_num++;
    
    /* Run logical tests */
    int logic = test_logical();
    if (logic == 7) total_result |= (1 << test_num);
    test_num++;
    
    /* Run shift tests */
    int shift = test_shifts();
    if (shift == 7) total_result |= (1 << test_num);
    test_num++;
    
    /* Run comparison tests */
    int cmp = test_comparisons();
    if (cmp == 31) total_result |= (1 << test_num);
    test_num++;
    
    /* Run memory tests */
    int mem = test_memory();
    if (mem == 15) total_result |= (1 << test_num);
    test_num++;
    
    /* Run loop tests */
    int loops = test_loops();
    if (loops == 7) total_result |= (1 << test_num);
    test_num++;
    
    /* Write final result (should be 0x3F = 63 if all tests pass) */
    write_result(total_result);
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
