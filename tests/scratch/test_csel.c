/* Test CSEL instruction directly */

__attribute__((noreturn))
void _start(void) {
    volatile int result = 0;
    volatile int a = 42;
    volatile int b = 42;  /* Same value for guaranteed equality */
    
    /* Simple comparison and conditional set */
    if (a == b) {
        result = 100;
    } else {
        result = 200;
    }
    
    /* Store to memory location for verification */
    volatile int *output = (volatile int *)0x100;
    *output = result;  /* Should be 100 */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
