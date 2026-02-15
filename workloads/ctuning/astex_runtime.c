#include <stdio.h>

#include <linxisa_libc.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

extern const unsigned char __astex_codelet_data[];
extern const unsigned char __astex_codelet_data_end[];

typedef struct AstexFile {
    const unsigned char *data;
    size_t size;
    size_t off;
} AstexFile;

static AstexFile g_file;

int __astex_write_message(const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    int r = vprintf(format, ap);
    va_end(ap);
    return r;
}

int __astex_write_output(const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    int r = vprintf(format, ap);
    va_end(ap);
    return r;
}

void __astex_exit_on_error(const char *msg, int code, const char *additional_msg)
{
    if (msg) {
        __astex_write_message("error: %s\n", msg);
    }
    if (additional_msg) {
        __astex_write_message("context: %s\n", additional_msg);
    }
    exit(code);
}

void *__astex_fopen(const char *name, const char *mode)
{
    (void)mode;
    (void)name;

    g_file.data = __astex_codelet_data;
    g_file.size = (size_t)(__astex_codelet_data_end - __astex_codelet_data);
    g_file.off = 0;
    return &g_file;
}

void *__astex_memalloc(long bytes)
{
    if (bytes <= 0) {
        return NULL;
    }
    return malloc((size_t)bytes);
}

void __astex_close_file(void *file)
{
    (void)file;
}

void __astex_read_from_file(void *dest, long bytes, void *file)
{
    if (!dest || bytes <= 0 || !file) {
        return;
    }

    AstexFile *f = (AstexFile *)file;
    size_t want = (size_t)bytes;
    size_t have = 0;

    if (f->off < f->size) {
        size_t avail = f->size - f->off;
        have = (want <= avail) ? want : avail;
        memcpy(dest, f->data + f->off, have);
        f->off += have;
    }

    if (have < want) {
        memset((unsigned char *)dest + have, 0, want - have);
    }
}

int __astex_getenv_int(const char *var)
{
    if (!var) {
        return 0;
    }
    if (strcmp(var, "CT_REPEAT_MAIN") == 0) {
        return 1;
    }
    return 0;
}

void *__astex_start_measure(void)
{
    return NULL;
}

double __astex_stop_measure(void *_before)
{
    (void)_before;
    return 0.0;
}

