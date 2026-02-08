/* Test large immediate instructions for LinxISA */

/* Define integer types for bare-metal */
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed short int16_t;
typedef unsigned short uint16_t;
typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef signed long long int64_t;
typedef unsigned long long uint64_t;

__attribute__((noreturn))
void _start(void) {
    volatile int result = 0;
    
    /* Test 20-bit immediate with LUI */
    volatile uint64_t val = 0;
    val = 0x12345000ULL;  /* Should use LUI for upper bits */
    if (val == 0x12345000ULL) {
        result += 1;
    }
    
    /* Test addition with larger values */
    volatile uint64_t base = 0x10000;
    volatile uint64_t sum = base + 0x5000;  /* Should use extended immediate */
    if (sum == 0x15000) {
        result += 2;
    }
    
    /* Test 32-bit constant materialization */
    volatile int32_t large_signed = 0x7FFFFFFF;  /* Max positive 32-bit */
    if (large_signed > 0) {
        result += 4;
    }
    
    /* Test negative 32-bit constant */
    large_signed = -0x7FFFFFFF;  /* Large negative */
    if (large_signed < 0) {
        result += 8;
    }
    
    /* Test address computation with offset */
    volatile uint64_t *ptr = (volatile uint64_t *)0x1000;
    volatile uint64_t addr = (uint64_t)(ptr + 10);  /* Should add 80 (10*8) */
    if (addr == 0x1050) {
        result += 16;
    }
    
    /* Write result to memory for verification */
    volatile int *output = (volatile int *)0x100;
    *output = result;  /* Should be 31 if all tests pass */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
