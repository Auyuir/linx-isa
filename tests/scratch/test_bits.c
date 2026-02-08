/* Test bit manipulation instructions for LinxISA */

/* Define integer types for bare-metal */
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed short int16_t;
typedef unsigned short uint16_t;
typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef signed long long int64_t;
typedef unsigned long long uint64_t;

/* Builtin implementations for CLZ, CTZ, POPCNT */
static inline int clz64(uint64_t x) {
    if (x == 0) return 64;
    int n = 0;
    if (x <= 0x00000000FFFFFFFFULL) { n += 32; x <<= 32; }
    if (x <= 0x0000FFFFFFFFFFFFULL) { n += 16; x <<= 16; }
    if (x <= 0x00FFFFFFFFFFFFFFULL) { n +=  8; x <<=  8; }
    if (x <= 0x0FFFFFFFFFFFFFFFULL) { n +=  4; x <<=  4; }
    if (x <= 0x3FFFFFFFFFFFFFFFULL) { n +=  2; x <<=  2; }
    if (x <= 0x7FFFFFFFFFFFFFFFULL) { n +=  1; }
    return n;
}

static inline int ctz64(uint64_t x) {
    if (x == 0) return 64;
    int n = 0;
    if ((x & 0x00000000FFFFFFFFULL) == 0) { n += 32; x >>= 32; }
    if ((x & 0x000000000000FFFFULL) == 0) { n += 16; x >>= 16; }
    if ((x & 0x00000000000000FFULL) == 0) { n +=  8; x >>=  8; }
    if ((x & 0x000000000000000FULL) == 0) { n +=  4; x >>=  4; }
    if ((x & 0x0000000000000003ULL) == 0) { n +=  2; x >>=  2; }
    if ((x & 0x0000000000000001ULL) == 0) { n +=  1; }
    return n;
}

static inline int popcnt64(uint64_t x) {
    int count = 0;
    while (x) {
        count += x & 1;
        x >>= 1;
    }
    return count;
}

__attribute__((noreturn))
void _start(void) {
    volatile uint64_t val1 = 0x8000000000000000ULL;  /* MSB set */
    volatile uint64_t val2 = 0x0000000000000001ULL;  /* LSB set */
    volatile uint64_t val3 = 0x00000000000000FFULL;  /* 8 bits set */
    
    volatile int *output = (volatile int *)0x100;
    int result = 0;
    
    /* Test CLZ - count leading zeros */
    int clz_result = clz64(val1);  /* Should be 0 */
    if (clz_result == 0) result += 1;
    
    clz_result = clz64(val2);  /* Should be 63 */
    if (clz_result == 63) result += 2;
    
    /* Test CTZ - count trailing zeros */
    int ctz_result = ctz64(val1);  /* Should be 63 */
    if (ctz_result == 63) result += 4;
    
    ctz_result = ctz64(val2);  /* Should be 0 */
    if (ctz_result == 0) result += 8;
    
    /* Test POPCNT - count 1 bits */
    int pop_result = popcnt64(val3);  /* Should be 8 */
    if (pop_result == 8) result += 16;
    
    *output = result;  /* Should be 31 if all tests pass */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
