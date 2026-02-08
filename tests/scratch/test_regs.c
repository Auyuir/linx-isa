/* Test that stores results for verification */

__attribute__((noreturn))
void _start(void) {
    /* Use volatile to prevent optimization */
    volatile unsigned int x = 0xFF00;
    volatile unsigned int y = 0x00FF;
    
    /* Store results to known memory locations */
    volatile unsigned int *mem = (volatile unsigned int *)0x100;
    
    mem[0] = x;           /* Should be 0xFF00 */
    mem[1] = y;           /* Should be 0x00FF */
    mem[2] = x | y;       /* Should be 0xFFFF */
    mem[3] = x & y;       /* Should be 0x0000 */
    mem[4] = x ^ y;       /* Should be 0xFFFF */
    mem[5] = x + y;       /* Should be 0xFFFF */
    
    /* Store a marker to verify we reached this point */
    mem[6] = 0xCAFE;
    
    /* Store result of comparison: 1 if OR worked, 0 otherwise */
    if ((x | y) == 0xFFFF) {
        mem[7] = 1;
    } else {
        mem[7] = 0;
    }
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
