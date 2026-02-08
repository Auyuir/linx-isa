/* Test 1: Simple conditional branch */
typedef long int64_t;
typedef unsigned long uint64_t;
typedef int int32_t;
typedef unsigned int uint32_t;

/* Simple function to test calls */
__attribute__((noinline))
int32_t add_func(int32_t a, int32_t b) {
    return a + b;
}

/* Test conditional branch */
__attribute__((noinline))
int32_t test_if(int32_t x) {
    if (x > 10) {
        return 1;
    } else {
        return 0;
    }
}

/* Test loop */
__attribute__((noinline))
int32_t test_loop(int32_t n) {
    int32_t sum = 0;
    for (int32_t i = 0; i < n; i++) {
        sum += i;
    }
    return sum;
}

__attribute__((noreturn))
void _start(void) {
    int32_t result = 0;
    
    /* Test 1: Simple addition function call */
    int32_t a = add_func(5, 3);  /* Should be 8 */
    if (a == 8) result |= 1;
    
    /* Test 2: Conditional branch (true case) */
    int32_t b = test_if(15);  /* Should be 1 */
    if (b == 1) result |= 2;
    
    /* Test 3: Conditional branch (false case) */
    int32_t c = test_if(5);  /* Should be 0 */
    if (c == 0) result |= 4;
    
    /* Test 4: Loop */
    int32_t d = test_loop(5);  /* Should be 0+1+2+3+4 = 10 */
    if (d == 10) result |= 8;
    
    /* result should be 0xF (15) if all tests pass */
    /* Store result in a0 for easy inspection */
    register int32_t r_result __asm__("a0") = result;
    (void)r_result;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
