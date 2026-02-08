/* Minimal function call test */
typedef int int32_t;

/* Simplest possible function */
__attribute__((noinline))
int32_t simple_return(int32_t x) {
    return x;  /* Just return the argument */
}

__attribute__((noreturn))
void _start(void) {
    register int32_t a0 __asm__("a0") = simple_return(42);
    (void)a0;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
