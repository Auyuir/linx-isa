/* Test compare immediate and conditional instructions for LinxISA */

__attribute__((noreturn))
void _start(void) {
    volatile int result = 0;
    volatile int a = 10;
    volatile int b = 20;
    volatile int c = -5;
    
    /* Test equal comparison */
    if (a == 10) {
        result += 1;  /* Should pass */
    }
    
    /* Test not equal comparison */
    if (a != 5) {
        result += 2;  /* Should pass */
    }
    
    /* Test less than (signed) */
    if (c < 0) {
        result += 4;  /* Should pass */
    }
    
    /* Test greater than or equal (signed) */
    if (a >= 5) {
        result += 8;  /* Should pass */
    }
    
    /* Test unsigned comparison */
    volatile unsigned int ua = 10;
    volatile unsigned int ub = 100;
    if (ua < ub) {
        result += 16;  /* Should pass */
    }
    
    /* Write result to memory for verification */
    volatile int *output = (volatile int *)0x100;
    *output = result;  /* Should be 31 if all tests pass */
    
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
