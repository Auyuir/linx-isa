/* Minimal test - just ebreak */
__attribute__((noreturn))
void _start(void) {
    __asm__ volatile ("ebreak 0" ::: "memory");
    __builtin_unreachable();
}
