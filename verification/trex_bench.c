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
 * Segment 2 additions:
 *   struct Shared  { int32_t a; char* name; int64_t v; };   (0,4)(8,8)(16,8) [interproc, deep]
 *   struct HasUnit { int32_t tag; struct Unit u; };         (0,4)(4,8)       [unit nesting]
 *   struct Unit    { int32_t x; int32_t y; };               (0,4)(4,4)
 *   struct List0   { struct List0* next; int32_t data; };   (0,8)(8,4)       [recursion @0]
 *   union  Mix     { uint32_t u32; uint8_t b[4]; };         (0,4)            [union]
 *
 * Segment 3 addition:
 *   struct NegInner { int32_t x; };                           (0,4)
 *   struct NegOuter { int32_t tag; struct NegInner inner; };   (0,4)(4,4)     [CONTAINING_RECORD via magic comment]
 * Built at -O0 (primary) and -O2 (robustness, mirrors TRex RQ3) with
 * -g0 so Hex-Rays gets no type hints — only symbol names.
 */
#include <stdint.h>
#include <stdlib.h>

volatile int g_sink = 0;
volatile void* g_psink = 0;

struct Simple  { int32_t a; int32_t b; int64_t c; };
struct Inner   { int32_t x; int32_t y; };
struct Shared  { int32_t a; char* name; int64_t v; };
struct Unit    { int32_t x; int32_t y; };
struct HasUnit { int32_t tag; struct Unit u; };
struct List0   { struct List0* next; int32_t data; };
union  Mix     { uint32_t u32; uint8_t b[4]; };
struct Nested  { int32_t tag; struct Inner in; };
struct List    { int32_t data; struct List* next; };
struct WithArr { int32_t prefix; int32_t items[8]; };
struct MultiW  { uint32_t whole; uint32_t after; };
struct Funcy   { int32_t id; int32_t (*cb)(int32_t); void* ctx; };
struct Shapes  { char tag; int64_t val; };
struct NegInner { int32_t x; };
struct NegOuter { int32_t tag; struct NegInner inner; };
struct Neg16Inner { int16_t x; };
struct Neg16Outer { int16_t tag; int16_t pad; struct Neg16Inner inner; };

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

/* --- Segment 2 --- */

__attribute__((noinline)) void helper_shared(struct Shared* s) {
    s->a = 1;
    s->name = "bench";
    s->v = 2;
}

__attribute__((noinline)) void bench_interproc(struct Shared* p) {
    helper_shared(p);
}

__attribute__((noinline)) void helper_unit(struct Unit* u) {
    u->x = 1;
    u->y = 2;
}

__attribute__((noinline)) void bench_unit(struct HasUnit* p) {
    p->tag = 1;
    helper_unit(&p->u);
}

__attribute__((noinline)) int bench_list0(struct List0* n) {
    int last = 0;
    while (n) {
        last = n->data;
        n = n->next;
    }
    return last;
}

__attribute__((noinline)) uint32_t bench_mix_wide(union Mix* m) {
    return m->u32;
}

__attribute__((noinline)) uint8_t bench_mix_narrow(union Mix* m) {
    return m->b[1];
}

/* Segment 3 — negative-offset (CONTAINING_RECORD) workflow.
 *
 * The function takes a pointer to NegInner and reaches back to the containing
 * NegOuter via the standard CONTAINING_RECORD idiom (subtracting the inner
 * offset from the pointer). After the bench harness programmatically applies
 * the magic comment ``NegOuter+0`` to the lvar, Hex-Rays' negative-offset
 * support rewrites the access into ``CONTAINING_RECORD(p, NegOuter, tag)``.
 * Without the magic comment the only field recovered is ``inner.x`` at offset 0
 * (the relative offset inside the inner struct).
 */
__attribute__((noinline)) int neg_offset_access(struct NegInner* p) {
    return ((struct NegOuter*)((char*)p - 4))->tag + p->x;
}

__attribute__((noinline)) int neg16_access(struct Neg16Inner* p) {
    return ((struct Neg16Outer*)((char*)p - 4))->tag + p->x;
}

/* NegOuter scanned with TWO functions — one for tag, one for inner — to
 * aggregate evidence across multiple CONTAINING_RECORD rewrite sites
 * (each `(Outer*)(p-4)` is independently rewritten into a helper call).
 */
__attribute__((noinline)) int neg_outer_tag(struct NegInner* p) {
    return ((struct NegOuter*)((char*)p - 4))->tag;
}
__attribute__((noinline)) int neg_outer_inner(struct NegInner* p) {
    struct NegOuter *outer = (struct NegOuter*)((char*)p - 4);
    return outer->inner.x;
}

static int cb_impl(int32_t x) { return (int)x * 3; }

int main(void) {
    struct Simple s = {0};
    struct Nested n = {0};
    struct WithArr w = {0};
    struct MultiW m = {0};
    struct Funcy f = {0};
    struct Shapes sh = {0};
    struct Shared sd = {0, 0, 0};
    struct HasUnit hu = {0};
    union Mix mx = {0};

    struct List l3 = {30, NULL};
    struct List l2 = {20, &l3};
    struct List l1 = {10, &l2};

    struct List0 l0b = {NULL, 30};
    struct List0 l0a = {&l0b, 10};

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
    bench_interproc(&sd);
    bench_unit(&hu);
    sink_i(bench_list0(&l0a));
    sink_i((int)bench_mix_wide(&mx));
    sink_i((int)bench_mix_narrow(&mx));
    g_psink = (void*)(intptr_t)sd.v;
    {
        struct NegInner ni = {0};
        sink_i(neg_offset_access(&ni));
        sink_i(neg_outer_tag(&ni));
        sink_i(neg_outer_inner(&ni));
    }
    {
        struct Neg16Inner n16 = {0};
        sink_i(neg16_access(&n16));
    }
    return g_sink == 0 && g_psink != 0 ? 0 : 1;
}
