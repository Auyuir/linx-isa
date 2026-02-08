/* Simple test for LinxISA instructions */

/* Define integer types for bare-metal */
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed short int16_t;
typedef unsigned short uint16_t;
typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef signed long long int64_t;
typedef unsigned long long uint64_t;

/* Helper to write result */
static inline void write_result(int value) {
    volatile int *output = (volatile int *)0x100;
    *output = value;
}

__attribute__((noreturn))
void _start(void) {
    int result = 0;
    
    /* Test 1: Basic arithmetic */
    volatile int a = 42;
    volatile int b = 13;
    
    if (a + b == 55) result |= 1;
    if (a - b == 29) result |= 2;
    if (a * b == 546) result |= 4;
    if (a / b == 3) result |= 8;
    if (a % b == 3) result |= 16;
    
    /* Test 2: Logical operations with small values */
    volatile uint32_t x = 0xFF00;
    volatile uint32_t y = 0x00FF;
    
    if ((x & y) == 0) result |= 32;
    if ((x | y) == 0xFFFF) result |= 64;
    if ((x ^ y) == 0xFFFF) result |= 128;
    
    /* Test 3: Shifts */
    volatile uint32_t val = 1;
    if ((val << 10) == 1024) result |= 256;
    if ((val << 20) == 0x100000) result |= 512;
    
    /* Test 4: Comparisons */
    volatile int c = -5;
    if (a > c) result |= 1024;
    if (c < 0) result |= 2048;
    
    /* Test 5: Loop */
    volatile int sum = 0;
    for (int i = 1; i <= 10; i++) {
        sum += i;
    }
    if (sum == 55) result |= 4096;
    
    /* Test 6: Memory operations */
    volatile uint32_t *p32 = (volatile uint32_t *)0x200;
    *p32 = 0x12345678;
    if (*p32 == 0x12345678) result |= 8192;
    
    /* All tests pass if result == 0x3FFF = 16383 */
    write_result(result);
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
