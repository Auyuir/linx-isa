#include <linxisa_libc.h>

extern int main(int argc, const char **argv);

void _start(void)
{
    static const char arg0[] = "milepost-codelet";
    static const char arg1[] = "codelet.data";
    const char *argv[3];
    argv[0] = arg0;
    argv[1] = arg1;
    argv[2] = 0;

    int rc = main(2, argv);
    __linx_exit(rc);
}
