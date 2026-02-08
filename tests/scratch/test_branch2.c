/* Test branches and function calls - volatile to prevent optimization */
typedef long int64_t;
typedef unsigned long uint64_t;
typedef int int32_t;
typedef unsigned int uint32_t;

volatile int32_t global_result;

/* Simple function to test calls */
__attribute__((noinline))
int32_t add_func(int32_t a, int32_t b) {
    return a + b;
}

__attribute__((noreturn))
void _start(void) {
    /* Test function call */
    global_result = add_func(5, 3);  /* Should be 8 */
    
    /* Store result in a0 for inspection */
    register int32_t r_result __asm__("a0") = global_result;
    (void)r_result;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
