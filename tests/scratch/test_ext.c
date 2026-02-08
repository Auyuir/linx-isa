/* Test sign/zero extension instructions for LinxISA */

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
    
    /* Test sign extension from byte */
    volatile int8_t sb = -5;  /* 0xFB */
    volatile int64_t se_result = (int64_t)sb;  /* Should be -5 (0xFFFFFFFFFFFFFFFB) */
    if (se_result == -5) {
        result += 1;
    }
    
    /* Test zero extension from byte */
    volatile uint8_t ub = 200;  /* 0xC8 */
    volatile uint64_t ze_result = (uint64_t)ub;  /* Should be 200 */
    if (ze_result == 200) {
        result += 2;
    }
    
    /* Test sign extension from halfword */
    volatile int16_t sh = -1000;  /* 0xFC18 */
    se_result = (int64_t)sh;  /* Should be -1000 */
    if (se_result == -1000) {
        result += 4;
    }
    
    /* Test zero extension from halfword */
    volatile uint16_t uh = 50000;  /* 0xC350 */
    ze_result = (uint64_t)uh;  /* Should be 50000 */
    if (ze_result == 50000) {
        result += 8;
    }
    
    /* Test sign extension from word */
    volatile int32_t sw = -100000;
    se_result = (int64_t)sw;  /* Should be -100000 */
    if (se_result == -100000) {
        result += 16;
    }
    
    /* Test zero extension from word */
    volatile uint32_t uw = 3000000000U;
    ze_result = (uint64_t)uw;  /* Should be 3000000000 */
    if (ze_result == 3000000000ULL) {
        result += 32;
    }
    
    /* Write result to memory for verification */
    volatile int *output = (volatile int *)0x100;
    *output = result;  /* Should be 63 if all tests pass */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
