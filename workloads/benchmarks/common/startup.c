#include <linxisa_libc.h>

extern int main(void);

void _start(void)
{
    int rc = main();
    __linx_exit(rc);
}

