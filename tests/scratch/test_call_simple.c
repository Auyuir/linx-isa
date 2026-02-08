/* Simple function call test using new calling convention */
typedef long int64_t;
typedef int int32_t;

volatile int32_t global_result;

/* Simple function - NOT inlined */
__attribute__((noinline))
int32_t add_one(int32_t x) {
    global_result = x + 100;  /* Prevent complete optimization */
    return x + 1;
}

__attribute__((noreturn))
void _start(void) {
    int32_t result = add_one(41);  /* Should return 42 */
    global_result = result;
    
    /* Store in a0 for inspection */
    register int32_t r __asm__("a0") = result;
    (void)r;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
