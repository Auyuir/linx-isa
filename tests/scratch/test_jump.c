/* Test simple jumps without function calls */
typedef int int32_t;

volatile int32_t result;

__attribute__((noreturn))
void _start(void) {
    result = 1;
    
    if (result) {
        result = 42;
    }
    
    register int32_t a0 __asm__("a0") = result;
    (void)a0;
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
