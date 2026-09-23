/* Type-reconstruction benchmark patterns for HexRaysPyTools-ng.
 *
 * Ground truth (x86-64, natural alignment) — keep in sync with
 * verification/trex_bench_ida.py BENCH and verification/score_trex_bench.py:
 *
 *   struct Simple  { int32_t a; int32_t b; int64_t c; };          (0,4)(4,4)(8,8)
 *   struct Inner   { int32_t x; int32_t y; };                     (0,4)(4,4)
 *   struct Nested  { int32_t tag; struct Inner in; };             (0,4)(4,8)
 *   struct List    { int32_t data; struct List* next; };          (0,4)(8,8)   [TRex Fig.4]
 *   struct WithArr { int32_t prefix; int32_t items[8]; };         (0,4)(4,32)  [dynamic offset]
 *   struct MultiW  { uint32_t whole; uint32_t after; };           (0,4)(4,4)   [multi-width]
 *   struct Funcy   { int32_t id; int32_t (*cb)(int32_t); void* ctx; } (0,4)(8,8)(16,8)
 *   struct Shapes  { char tag; int64_t val; };                    (0,1)(8,8)   [gap/padding]
 *
 * Built at -O0 (primary) and -O2 (robustness, mirrors TRex RQ3) with
 * -g0 so Hex-Rays gets no type hints — only symbol names.
 */
#include <stdint.h>
#include <stdlib.h>

volatile int g_sink = 0;
volatile void* g_psink = 0;

struct Simple  { int32_t a; int32_t b; int64_t c; };
struct Inner   { int32_t x; int32_t y; };
struct Nested  { int32_t tag; struct Inner in; };
struct List    { int32_t data; struct List* next; };
struct WithArr { int32_t prefix; int32_t items[8]; };
struct MultiW  { uint32_t whole; uint32_t after; };
struct Funcy   { int32_t id; int32_t (*cb)(int32_t); void* ctx; };
struct Shapes  { char tag; int64_t val; };

__attribute__((noinline)) static void sink_i(int v) { g_sink = v; }
__attribute__((noinline)) static void sink_p(void* p) { g_psink = p; }

__attribute__((noinline)) void bench_simple(struct Simple* p) {
    p->a = 1;
    p->b = 2;
    sink_i((int)(p->a + p->b + (int)p->c));
}

__attribute__((noinline)) void bench_nested(struct Nested* p) {
    p->tag = 1;
    p->in.x = 2;
    p->in.y = 3;
    sink_i(p->tag + p->in.x + p->in.y);
}

/* TRex paper Figure 4: singly-linked list walk (recursion at offset 8). */
__attribute__((noinline)) int bench_list_walk(struct List* n) {
    int last = 0;
    while (n) {
        last = n->data;
        n = n->next;
    }
    return last;
}

/* Dynamic offset: loop over items[] — decompiles to *(base + i*4). */
__attribute__((noinline)) int bench_array_sum(struct WithArr* p) {
    int s = p->prefix;
    for (int i = 0; i < 8; i++)
        s += p->items[i];
    return s;
}

/* Static indices on the same array. */
__attribute__((noinline)) int bench_array_static(struct WithArr* p) {
    p->prefix = 1;
    p->items[3] = 7;
    return p->items[3] + p->prefix;
}

__attribute__((noinline)) uint32_t bench_multi_wide(struct MultiW* p) {
    return p->whole + p->after;
}

/* Same struct touched byte-wide (offset 1) — multi-width evidence. */
__attribute__((noinline)) uint32_t bench_multi_narrow(struct MultiW* p) {
    unsigned char* b = (unsigned char*)p;
    b[1] = 0x41;
    return p->whole + p->after;
}

__attribute__((noinline)) int bench_funcy(struct Funcy* p) {
    p->id = 1;
    p->ctx = 0;
    return p->cb ? p->cb(p->id) : -1;
}

__attribute__((noinline)) int64_t bench_shapes(struct Shapes* p) {
    p->tag = 'x';
    p->val += 1;
    return p->val;
}

static int cb_impl(int32_t x) { return (int)x * 3; }

int main(void) {
    struct Simple s = {0};
    struct Nested n = {0};
    struct WithArr w = {0};
    struct MultiW m = {0};
    struct Funcy f = {0};
    struct Shapes sh = {0};

    struct List l3 = {30, NULL};
    struct List l2 = {20, &l3};
    struct List l1 = {10, &l2};

    bench_simple(&s);
    bench_nested(&n);
    sink_i(bench_list_walk(&l1));
    sink_i(bench_array_sum(&w));
    sink_i(bench_array_static(&w));
    sink_i((int)bench_multi_wide(&m));
    sink_i((int)bench_multi_narrow(&m));
    f.cb = cb_impl;
    sink_i(bench_funcy(&f));
    g_psink = (void*)(intptr_t)bench_shapes(&sh);
    return g_sink == 0 && g_psink != 0 ? 0 : 1;
}
