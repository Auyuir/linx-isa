/* Hello world using linx-libc printf on QEMU. */

#include <linxisa_libc.h>

int main(void);

void _start(void) {
    int rc = main();
    __linx_exit(rc);
}

int main(void) {
    printf("Hello world from Linx printf!\n");
    printf("dec=%d hex=%08x ptr=%p str=%s char=%c\n",
           -42, 0x1234abcdU, (void *)0x10000000ULL, "ok", '!');
    return 0;
}
