/* Test min/max instructions for LinxISA */

__attribute__((noreturn))
void _start(void) {
    volatile int a = 10;
    volatile int b = 25;
    volatile int c = -5;
    volatile int result;
    
    /* Test min (signed) */
    if (a < b) {
        result = a;  /* Should be 10 */
    } else {
        result = b;
    }
    
    /* Test max (signed) */
    if (a > c) {
        result = a;  /* Should be 10 */
    } else {
        result = c;
    }
    
    /* Test min with negative */
    if (c < a) {
        result = c;  /* Should be -5 */
    } else {
        result = a;
    }
    
    /* Write result to memory location for verification */
    volatile int *output = (volatile int *)0x100;
    *output = result;
    
    /* Exit via ebreak */
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
