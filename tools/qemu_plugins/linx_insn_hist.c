/*
 * Linx instruction histogram plugin.
 *
 * Collects a dynamic instruction histogram keyed by the first token of
 * QEMU's per-instruction disassembly string.
 *
 * Intended for bring-up benchmarking: correctness/perf regression signals
 * are more useful when we can see which opcodes dominate execution.
 */

#include <glib.h>
#include <inttypes.h>
#include <qemu-plugin.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>

#include "linxisa_opcodes.h"

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

typedef struct Counter {
    const char *mnemonic; /* interned */
    _Atomic uint64_t count;
} Counter;

static gchar *out_path;
static guint top_n = 50;

static GHashTable *mnemonic_to_counter; /* key: interned mnemonic -> Counter* */
static GPtrArray *all_counters;         /* Counter* */
static GMutex map_lock;

static _Atomic uint64_t total_insns;

static const char *extract_mnemonic_token(const char *disas)
{
    if (!disas) {
        return "";
    }
    const char *p = disas;
    while (*p == ' ' || *p == '\t') {
        p++;
    }
    const char *start = p;
    while (*p && *p != ' ' && *p != '\t' && *p != ',' && *p != '\n') {
        p++;
    }
    if (p <= start) {
        return "";
    }
    g_autofree gchar *tmp = g_strndup(start, (gsize)(p - start));
    /* Normalize for stable keys. */
    g_strstrip(tmp);
    if (tmp[0] == '\0') {
        return "";
    }
    return g_intern_string(tmp);
}

static const char *decode_mnemonic_from_bytes(const void *buf, size_t size_bytes)
{
    uint64_t val = 0;
    const uint8_t *b = (const uint8_t *)buf;
    if (size_bytes == 0 || size_bytes > 8) {
        return g_intern_string("ILLEGAL");
    }
    for (size_t i = 0; i < size_bytes; i++) {
        val |= ((uint64_t)b[i]) << (8u * (unsigned)i);
    }

    const unsigned bits = (unsigned)(size_bytes * 8u);
    const linxisa_inst_form *best = NULL;
    unsigned best_fixed = 0;
    for (size_t i = 0; i < linxisa_inst_forms_count; i++) {
        const linxisa_inst_form *f = &linxisa_inst_forms[i];
        if ((unsigned)f->length_bits != bits) {
            continue;
        }
        if ((val & f->mask) != f->match) {
            continue;
        }
        unsigned fixed = (unsigned)__builtin_popcountll((unsigned long long)f->mask);
        if (!best || fixed > best_fixed) {
            best = f;
            best_fixed = fixed;
        }
    }
    if (!best || !best->mnemonic || best->mnemonic[0] == '\0') {
        return g_intern_string("ILLEGAL");
    }
    return g_intern_string(best->mnemonic);
}

static Counter *get_counter(const char *mnemonic_interned)
{
    Counter *c;
    g_mutex_lock(&map_lock);
    c = g_hash_table_lookup(mnemonic_to_counter, mnemonic_interned);
    if (!c) {
        c = g_new0(Counter, 1);
        c->mnemonic = mnemonic_interned;
        c->count = 0;
        g_hash_table_insert(mnemonic_to_counter, (gpointer)mnemonic_interned, c);
        g_ptr_array_add(all_counters, c);
    }
    g_mutex_unlock(&map_lock);
    return c;
}

static void vcpu_insn_exec(unsigned int cpu_index, void *udata)
{
    (void)cpu_index;
    Counter *c = (Counter *)udata;
    atomic_fetch_add_explicit(&c->count, 1, memory_order_relaxed);
    atomic_fetch_add_explicit(&total_insns, 1, memory_order_relaxed);
}

static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    (void)id;
    size_t n_insns = qemu_plugin_tb_n_insns(tb);
    for (size_t i = 0; i < n_insns; i++) {
        struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
        uint8_t buf[8];
        size_t sz = qemu_plugin_insn_size(insn);
        size_t got = qemu_plugin_insn_data(insn, buf, sizeof(buf));
        if (got < sz) {
            sz = got;
        }
        const char *mnem = decode_mnemonic_from_bytes(buf, sz);
        Counter *c = get_counter(mnem);
        qemu_plugin_register_vcpu_insn_exec_cb(insn, vcpu_insn_exec,
                                               QEMU_PLUGIN_CB_NO_REGS, c);
    }
}

static gint sort_by_count_desc(gconstpointer a, gconstpointer b)
{
    const Counter *ca = *(Counter *const *)a;
    const Counter *cb = *(Counter *const *)b;
    uint64_t da = atomic_load_explicit(&ca->count, memory_order_relaxed);
    uint64_t db = atomic_load_explicit(&cb->count, memory_order_relaxed);
    if (da < db) {
        return 1;
    }
    if (da > db) {
        return -1;
    }
    return g_strcmp0(ca->mnemonic, cb->mnemonic);
}

static void write_report(void)
{
    if (!out_path || out_path[0] == '\0') {
        return;
    }

    g_ptr_array_sort(all_counters, sort_by_count_desc);

    FILE *fp = fopen(out_path, "w");
    if (!fp) {
        return;
    }

    const uint64_t total = atomic_load_explicit(&total_insns, memory_order_relaxed);
    fprintf(fp, "{\n");
    fprintf(fp, "  \"total_insns\": %" PRIu64 ",\n", total);
    fprintf(fp, "  \"top_n\": %u,\n", top_n);
    fprintf(fp, "  \"top\": [\n");

    guint emitted = 0;
    for (guint i = 0; i < all_counters->len && emitted < top_n; i++) {
        Counter *c = g_ptr_array_index(all_counters, i);
        uint64_t v = atomic_load_explicit(&c->count, memory_order_relaxed);
        if (v <= 0) {
            continue;
        }
        const double pct = (total > 0) ? (100.0 * (double)v / (double)total) : 0.0;
        if (emitted != 0) {
            fprintf(fp, ",\n");
        }
        fprintf(fp,
                "    {\"mnemonic\":\"%s\",\"count\":%" PRIu64 ",\"pct\":%.6f}",
                c->mnemonic, v, pct);
        emitted++;
    }
    fprintf(fp, "  ],\n");

    fprintf(fp, "  \"all\": {\n");
    bool first = true;
    for (guint i = 0; i < all_counters->len; i++) {
        Counter *c = g_ptr_array_index(all_counters, i);
        uint64_t v = atomic_load_explicit(&c->count, memory_order_relaxed);
        if (v <= 0) {
            continue;
        }
        if (!first) {
            fprintf(fp, ",\n");
        }
        first = false;
        fprintf(fp, "    \"%s\": %" PRIu64, c->mnemonic, v);
    }
    fprintf(fp, "\n  }\n");
    fprintf(fp, "}\n");
    fclose(fp);
}

static void plugin_exit(qemu_plugin_id_t id, void *udata)
{
    (void)id;
    (void)udata;
    write_report();
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                          const qemu_info_t *info,
                                          int argc, char **argv)
{
    (void)info;

    for (int i = 0; i < argc; i++) {
        char *opt = argv[i];
        g_auto(GStrv) tokens = g_strsplit(opt, "=", 2);
        if (g_strcmp0(tokens[0], "out") == 0) {
            g_free(out_path);
            out_path = g_strdup(tokens[1] ? tokens[1] : "");
        } else if (g_strcmp0(tokens[0], "top") == 0) {
            top_n = (guint)g_ascii_strtoull(tokens[1] ? tokens[1] : "50", NULL, 10);
            if (top_n == 0) {
                top_n = 50;
            }
        } else {
            fprintf(stderr, "linx_insn_hist: unknown option: %s\n", opt);
            return -1;
        }
    }

    mnemonic_to_counter = g_hash_table_new(g_str_hash, g_str_equal);
    all_counters = g_ptr_array_new();
    g_mutex_init(&map_lock);
    atomic_store_explicit(&total_insns, 0, memory_order_relaxed);

    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);
    return 0;
}
