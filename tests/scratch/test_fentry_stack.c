int global_result;

int caller(int x);

void test(int a) {
    // Need to call another function to force stack frame
    int result = caller(a);
    global_result = result;
}
