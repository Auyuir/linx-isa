/* Test PC-relative addressing without function calls */
typedef long int64_t;
typedef int int32_t;

volatile int32_t global_val = 42;

__attribute__((noreturn))
void _start(void) {
    /* Read the global value using PC-relative addressing */
    int32_t x = global_val;
    
    /* Modify and write back */
    global_val = x + 1;
    
    /* Store result in a0 for inspection */
    register int32_t r_result __asm__("a0") = global_val;
    (void)r_result;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
