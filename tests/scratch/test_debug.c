/* Debug test for LinxISA instructions */

typedef unsigned int uint32_t;

__attribute__((noreturn))
void _start(void) {
    volatile int result = 0;
    volatile uint32_t *out = (volatile uint32_t *)0x100;
    
    /* Test OR operation */
    volatile uint32_t x = 0xFF00;
    volatile uint32_t y = 0x00FF;
    volatile uint32_t or_result = x | y;
    
    out[0] = x;         /* Should be 0xFF00 */
    out[1] = y;         /* Should be 0x00FF */
    out[2] = or_result; /* Should be 0xFFFF */
    
    if (or_result == 0xFFFF) {
        result = 1;
    } else {
        result = 0;
    }
    
    /* Store the result and the actual or_result for debugging */
    out[3] = result;
    out[4] = 0xDEAD;  /* Marker to know we reached this point */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
