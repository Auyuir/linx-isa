// Simple test with stack frame but no calls
volatile int global_result = 0;

void _start(void) {
    // Force stack allocation with a local array
    volatile int local_array[4];
    local_array[0] = 10;
    local_array[1] = 20;
    local_array[2] = 30;
    local_array[3] = 40;
    global_result = local_array[0] + local_array[1] + local_array[2] + local_array[3];  // Should be 100
    __asm__ volatile("ebreak 0");
}
