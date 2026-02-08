#include <stdlib.h>
#include <stdint.h>

/* Minimal PolyBench/C runtime for Linx freestanding bring-up.
 *
 * The upstream PolyBench `utilities/polybench.c` depends on hosted/POSIX APIs
 * (gettimeofday, sched, resource limits, etc.). For the Linx bring-up profile
 * we only need allocation helpers and optional timer stubs.
 */

double polybench_program_total_flops = 0;

void *polybench_alloc_data(unsigned long long n, int elt_size)
{
    if (elt_size <= 0) {
        return NULL;
    }
    unsigned long long bytes = n * (unsigned long long)(unsigned)elt_size;
    if (n != 0 && (bytes / n) != (unsigned long long)(unsigned)elt_size) {
        return NULL;
    }
    if (bytes > (unsigned long long)SIZE_MAX) {
        return NULL;
    }
    return malloc((size_t)bytes);
}

void polybench_free_data(void *ptr)
{
    free(ptr);
}

void polybench_timer_start(void) {}
void polybench_timer_stop(void) {}
void polybench_timer_print(void) {}

void polybench_flush_cache(void) {}
void polybench_prepare_instruments(void) {}
