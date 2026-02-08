/* Test subi instruction */
__attribute__((noreturn))
void _start(void) {
    register volatile long sp_val __asm__("sp");
    sp_val = sp_val - 136;  /* Should generate subi sp, 136, ->sp */
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
