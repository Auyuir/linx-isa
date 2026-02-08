// Global result
volatile int global_result = 0;

// Force function call with noinline
__attribute__((noinline))
int add_values(int a, int b) {
    global_result = a + b;
    return a + b;
}

void _start(void) {
    int result = add_values(10, 32);
    global_result = result;  // Should be 42
    __asm__ volatile("ebreak 0");
}
