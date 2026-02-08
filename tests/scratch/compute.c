/* Test computation - stores result in A0 register (r2) before exit */
__attribute__((noreturn))
void _start(void) {
    volatile int result = 0;
    
    /* Simple computation: 1 + 2 + 3 + ... + 10 = 55 */
    for (int i = 1; i <= 10; i++) {
        result += i;
    }
    
    /* Store result in memory location that we can verify */
    volatile int *output = (volatile int *)0x100;  /* Small address that's in RAM */
    *output = result;
    
    /* Exit with EBREAK */
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
