/* Simple hello world for linx */
#include <stdint.h>

/* Use EBREAK to terminate the program - QEMU will intercept this */
static inline void linx_exit(int code) {
    __asm__ volatile ("c.ebreak" ::: "memory");
}

/* Simple memory write for debugging - write to a debug port */
volatile uint64_t *debug_port = (volatile uint64_t *)0x10000000;

void _start(void) {
    /* Write a marker to indicate program started */
    *debug_port = 0x48454C4C4F0A0000ULL; /* "HELLO\n" */
    
    /* Exit */
    linx_exit(0);
}
