/* Simple function call test */
typedef long int64_t;
typedef int int32_t;

volatile int32_t result;

/* Simple function */
__attribute__((noinline))
int32_t add_two(int32_t x) {
    return x + 2;
}

__attribute__((noreturn))
void _start(void) {
    /* Call function */
    result = add_two(5);  /* Should be 7 */
    
    /* Store in a0 for inspection */
    register int32_t r __asm__("a0") = result;
    (void)r;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
