/* Very simple test - just exit with noreturn */
__attribute__((noreturn))
void _start(void) {
    /* Use EBREAK to terminate - 32-bit instruction with imm=0 */
    __asm__ volatile ("ebreak 0" ::: "memory");
    /* This should never be reached but prevents implicit return */
    __builtin_unreachable();
}
