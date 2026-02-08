// Final comprehensive test for LinxISA FENTRY/FRET.STK
volatile int global_result = 0;

void _start(void) {
    // Test local variable allocation (uses FENTRY stack)
    int a = 10;
    int b = 32;
    int sum = a + b;
    global_result = sum;  // Should be 42
    
    // Trigger graceful exit
    __asm__ volatile("ebreak 0");
}
