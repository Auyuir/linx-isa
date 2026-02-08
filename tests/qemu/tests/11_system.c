/*
 * LinxISA System/Privilege Unit Tests (QEMU)
 *
 * This suite validates:
 * - Base SSR access (SSRGET/SSRSET/SSRSWAP) including symbolic SSR names
 * - HL.SSRGET/HL.SSRSET for extended SSR IDs (e.g. 0x1Fxx)
 * - ACRE/ACRC context switches (SERVICE_REQUEST + ACR_ENTER)
 * - A basic timer interrupt routed to ACR0
 *
 * Notes:
 * - Handlers are written in assembly to avoid stack/prologue side effects,
 *   because QEMU vectors to EVBASE by setting PC (not by a normal call/return).
 * - Continuation PCs are passed via scratch SSRs (0x0033..0x0035) using
 *   addresses of `noreturn` C stage functions (function-entry markers are
 *   valid block start targets in the Linx Block ISA bring-up rules).
 */

#include "linx_test.h"
#include <stdint.h>

/* Scratch SSRs (non-privileged) used for test communication. */
enum {
    SSR_SCRATCH0 = 0x0030, /* general R/W */
    SSR_SYSCALL_SEEN = 0x0031,
    SSR_IRQ_SEEN = 0x0032,
    SSR_CONT_SYSCALL = 0x0033,
    SSR_CONT_IRQ = 0x0034,
    SSR_CONT_EXIT = 0x0035,
};

/* Managing-ACR SSR IDs (ACR0 fits in 12-bit; ACR1 requires HL). */
enum {
    SSR_ECSTATE_ACR0 = 0x0F00,
    SSR_EVBASE_ACR0 = 0x0F01,
    SSR_EBPC_ACR0 = 0x0F0B,
    SSR_TIMER_TIMECMP_ACR0 = 0x0F21,

    SSR_EVBASE_ACR1 = 0x1F01,
    SSR_EBPC_ACR1 = 0x1F0B,
};

/* Test IDs */
enum {
    TESTID_SSR_BASIC = 0x1100,
    TESTID_SSR_HL = 0x1101,
    TESTID_PRIV_FLOW = 0x1102,
};

__attribute__((noreturn)) static void linx_priv_user_code(void);
__attribute__((noreturn)) static void linx_priv_after_syscall(void);
__attribute__((noreturn)) static void linx_priv_after_irq(void);
__attribute__((noreturn)) static void linx_priv_after_exit(void);

static inline uint64_t ssrget_uimm(uint32_t ssrid)
{
    uint64_t out;
    __asm__ volatile("ssrget %1, ->%0" : "=r"(out) : "i"(ssrid) : "memory");
    return out;
}

static inline void ssrset_uimm(uint32_t ssrid, uint64_t value)
{
    __asm__ volatile("ssrset %0, %1" : : "r"(value), "i"(ssrid) : "memory");
}

static inline uint64_t ssrswap_uimm(uint32_t ssrid, uint64_t value)
{
    uint64_t old;
    __asm__ volatile("ssrswap %1, %2, ->%0" : "=r"(old) : "r"(value), "i"(ssrid) : "memory");
    return old;
}

static inline uint64_t ssrget_time_symbol(void)
{
    uint64_t out;
    __asm__ volatile("ssrget TIME, ->%0" : "=r"(out) : : "memory");
    return out;
}

static inline uint64_t ssrget_cycle_symbol(void)
{
    uint64_t out;
    /* Ensures LLVM's assembler maps CYCLE to 0x0C00 (per isa-draft). */
    __asm__ volatile("ssrget CYCLE, ->%0" : "=r"(out) : : "memory");
    return out;
}

static inline uint64_t hl_ssrget_uimm24(uint32_t ssrid)
{
    uint64_t out;
    __asm__ volatile("hl.ssrget %1, ->%0" : "=r"(out) : "i"(ssrid) : "memory");
    return out;
}

static inline void hl_ssrset_uimm24(uint32_t ssrid, uint64_t value)
{
    __asm__ volatile("hl.ssrset %0, %1" : : "r"(value), "i"(ssrid) : "memory");
}

extern void linx_acr1_syscall_handler(void);
extern void linx_acr0_timer_handler(void);
extern void linx_acr0_exit_handler(void);

/* ACR1 syscall handler:
 * - mark seen (SSR_SYSCALL_SEEN=1)
 * - read continuation PC from SSR_CONT_SYSCALL
 * - write EBPC_ACR1 to continuation and return via ACRE
 */
__asm__(
    ".globl linx_acr1_syscall_handler\n"
    "linx_acr1_syscall_handler:\n"
    "  C.BSTART\n"
    "  ssrget 0x0033, ->a0\n"   /* continuation PC */
    "  addi zero, 1, ->a1\n"
    "  ssrset a1, 0x0031\n"     /* syscall seen */
    "  hl.ssrset a0, 0x1f0b\n"  /* EBPC_ACR1 = cont */
    "  acre 0\n"
);

/* ACR0 timer interrupt handler:
 * - mark seen (SSR_IRQ_SEEN=1)
 * - cancel TIMECMP (disable re-fire)
 * - read continuation PC from SSR_CONT_IRQ
 * - write EBPC_ACR0 and return via ACRE
 */
__asm__(
    ".globl linx_acr0_timer_handler\n"
    "linx_acr0_timer_handler:\n"
    "  C.BSTART\n"
    "  addi zero, 1, ->a1\n"
    "  ssrset a1, 0x0032\n"     /* irq seen */
    "  addi zero, 0, ->a1\n"
    "  ssrset a1, 0x0f21\n"     /* TIMECMP=0 (cancel) */
    "  ssrget 0x0034, ->a0\n"   /* continuation PC */
    "  ssrset a0, 0x0f0b\n"     /* EBPC_ACR0 = cont */
    "  acre 0\n"
);

/* ACR0 exit handler (service request from ACR2):
 * - set ECSTATE_ACR0.ACR = 0 (return to ACR0)
 * - read continuation PC from SSR_CONT_EXIT
 * - write EBPC_ACR0 and return via ACRE
 */
__asm__(
    ".globl linx_acr0_exit_handler\n"
    "linx_acr0_exit_handler:\n"
    "  C.BSTART\n"
    "  addi zero, 0, ->a1\n"
    "  ssrset a1, 0x0f00\n"     /* target ACR0 */
    "  ssrget 0x0035, ->a0\n"   /* continuation PC */
    "  ssrset a0, 0x0f0b\n"     /* EBPC_ACR0 = cont */
    "  acre 0\n"
);

__attribute__((noreturn)) static void linx_priv_user_code(void)
{
    /* ACR2: request a syscall (SCT_SYS) which routes to ACR1. */
    __asm__ volatile("acrc 1" : : : "memory");
    __builtin_unreachable();
}

__attribute__((noreturn)) static void linx_priv_after_syscall(void)
{
    /* Verify that the syscall handler ran. */
    TEST_EQ64(ssrget_uimm(SSR_SYSCALL_SEEN), 1, TESTID_PRIV_FLOW + 1);

    /*
     * Wait until the timer interrupt is delivered.
     *
     * The interrupt handler returns directly to `linx_priv_after_irq` by
     * setting EBPC_ACR0 to SSR_CONT_IRQ.
     */
    const uint64_t deadline = ssrget_time_symbol() + 20000000ull; /* 20ms */
    while (ssrget_time_symbol() < deadline) {
        /* spin */
    }

    test_fail(TESTID_PRIV_FLOW + 2, 1, ssrget_uimm(SSR_IRQ_SEEN));
}

__attribute__((noreturn)) static void linx_priv_after_irq(void)
{
    TEST_EQ64(ssrget_uimm(SSR_IRQ_SEEN), 1, TESTID_PRIV_FLOW + 3);

    /* Switch ACR0 vector to the exit handler, then request a service exit. */
    ssrset_uimm(SSR_EVBASE_ACR0, (uint64_t)(uintptr_t)&linx_acr0_exit_handler);
    __asm__ volatile("acrc 0" : : : "memory"); /* SCT_MAC -> routes to ACR0 */
    __builtin_unreachable();
}

__attribute__((noreturn)) static void linx_priv_after_exit(void)
{
    test_pass();

    /* End the program (system suite is last when enabled). */
    uart_puts("*** REGRESSION PASSED ***\r\n");
    EXIT_CODE = 0;
    while (1) {
        /* If QEMU doesn't exit for some reason, don't fall through. */
    }
}

void run_system_tests(void)
{
    test_suite_begin(0x53595354u); /* 'SYST' */

    /* --------------------------------------------------------------------- */
    /* Base SSR access + symbolic IDs                                         */
    /* --------------------------------------------------------------------- */
    test_start(TESTID_SSR_BASIC);

    ssrset_uimm(SSR_SCRATCH0, 0x1122334455667788ull);
    TEST_EQ64(ssrget_uimm(SSR_SCRATCH0), 0x1122334455667788ull, TESTID_SSR_BASIC);

    TEST_EQ64(ssrswap_uimm(SSR_SCRATCH0, 0xAABBCCDDEEFF0011ull),
              0x1122334455667788ull,
              TESTID_SSR_BASIC + 1);
    TEST_EQ64(ssrget_uimm(SSR_SCRATCH0), 0xAABBCCDDEEFF0011ull, TESTID_SSR_BASIC + 2);

    /* TIME should be monotonic. */
    uint64_t t0 = ssrget_time_symbol();
    for (volatile int i = 0; i < 1000; i++) {
        /* busy */
    }
    uint64_t t1 = ssrget_time_symbol();
    TEST_ASSERT(t1 >= t0, TESTID_SSR_BASIC + 3, t0, t1);

    /* CYCLE symbolic name must map to 0x0C00 (QEMU models as insn_count). */
    uint64_t c0 = ssrget_cycle_symbol();
    for (volatile int i = 0; i < 1000; i++) {
        /* busy */
    }
    uint64_t c1 = ssrget_cycle_symbol();
    TEST_ASSERT(c1 >= c0, TESTID_SSR_BASIC + 4, c0, c1);

    test_pass();

    /* --------------------------------------------------------------------- */
    /* HL.SSRGET/HL.SSRSET (extended IDs)                                     */
    /* --------------------------------------------------------------------- */
    test_start(TESTID_SSR_HL);

    /* Use an ACR1-only manager SSR ID to force HL forms (0x1F10). */
    hl_ssrset_uimm24(0x1F10u, 0x55aa1234ull);
    TEST_EQ64(hl_ssrget_uimm24(0x1F10u), 0x55aa1234ull, TESTID_SSR_HL);

    test_pass();

    /* --------------------------------------------------------------------- */
    /* Context switch + service request + timer interrupt                     */
    /* --------------------------------------------------------------------- */
    test_start(TESTID_PRIV_FLOW);

    /* Clear flags + publish continuation PCs via scratch SSRs. */
    ssrset_uimm(SSR_SYSCALL_SEEN, 0);
    ssrset_uimm(SSR_IRQ_SEEN, 0);
    ssrset_uimm(SSR_CONT_SYSCALL, (uint64_t)(uintptr_t)&linx_priv_after_syscall);
    ssrset_uimm(SSR_CONT_IRQ, (uint64_t)(uintptr_t)&linx_priv_after_irq);
    ssrset_uimm(SSR_CONT_EXIT, (uint64_t)(uintptr_t)&linx_priv_after_exit);

    /* Install handler vectors. */
    hl_ssrset_uimm24(SSR_EVBASE_ACR1, (uint64_t)(uintptr_t)&linx_acr1_syscall_handler);
    ssrset_uimm(SSR_EVBASE_ACR0, (uint64_t)(uintptr_t)&linx_acr0_timer_handler);

    /* Schedule a timer interrupt (ACR0) slightly in the future. */
    uint64_t now = ssrget_time_symbol();
    ssrset_uimm(SSR_TIMER_TIMECMP_ACR0, now + 1000000ull); /* +1ms */

    /* Hand off to ACR2 at the user-code stage function. */
    ssrset_uimm(SSR_ECSTATE_ACR0, 2); /* target ACR2 (low bits) */
    ssrset_uimm(SSR_EBPC_ACR0, (uint64_t)(uintptr_t)&linx_priv_user_code);
    __asm__ volatile("acre 0" : : : "memory");
    __builtin_unreachable();
}
