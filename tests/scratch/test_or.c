/* Ultra simple OR test */

__attribute__((noreturn))
void _start(void) {
    /* Store values directly */
    volatile unsigned int *out = (volatile unsigned int *)0x100;
    
    volatile unsigned int x = 0xFF00;
    volatile unsigned int y = 0x00FF;
    
    /* Store inputs */
    out[0] = x;
    out[1] = y;
    
    /* Compute and store OR */
    out[2] = x | y;
    
    /* Also compute AND, XOR */
    out[3] = x & y;
    out[4] = x ^ y;
    
    /* Store expected values */
    out[5] = 0xFFFF;  /* expected x | y */
    out[6] = 0x0;     /* expected x & y */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
