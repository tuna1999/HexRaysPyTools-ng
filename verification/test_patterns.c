#include <stdint.h>
#include <stdlib.h>

/* anti-dead-code sink: defined here (not just `extern`) so the linker
   has a symbol to resolve. `volatile` forces every read/write to hit
   memory, defeating any residual optimizer cleverness at -O0. */
volatile int g_sink = 0;
volatile int g_sink2 = 0;

/* --- Group 1: Scanner (struct pointer field access) --- */
struct ScanTarget {
    int   field_a;            /* offset 0 */
    int   field_b;            /* offset 4 */
    void* field_c;            /* offset 8 */
};

__attribute__((noinline))
void scan_simple(struct ScanTarget* p) {
    p->field_a = 1;
    p->field_b = p->field_a + 1;
    g_sink = p->field_b;
}

__attribute__((noinline))
void scan_chain(struct ScanTarget* p) {
    struct ScanTarget* q = p;     /* assignment chain for ObjectDownwardsVisitor */
    q->field_a = 42;
    g_sink = q->field_a;
}

/* --- Group 2: Rename (assignment chains + call args) ---
   NOTE: names are MEANINGFUL on purpose — _should_be_renamed() rejects
   auto-generated names (a1, v2, ...), so 'a1 = a2' would never rename.
   hide_value() is an opaque noinline sink: taking the address stops
   Hex-Rays from copy-propagating the assignment away. */
__attribute__((noinline))
void hide_value(int* sink) { g_sink = *sink; }

__attribute__((noinline))
void rename_assign_chain(int real_name, int passed_value) {
    int target = passed_value;    /* RenameOther target: target <- passed_value */
    hide_value(&target);          /* address escapes -> asg materializes */
    g_sink = target + real_name;
}

__attribute__((noinline))
void callee_takes_arg(int meaningful) {
    g_sink = meaningful;
}

__attribute__((noinline))
void rename_call_arg(int real_value) {
    int holder = real_value;
    hide_value(&holder);          /* address escapes -> holder materializes */
    callee_takes_arg(holder);     /* RenameOutside target: holder <- "meaningful" */
}

/* --- Group 3: Swap-if (if/else + spaghetti) --- */
__attribute__((noinline))
int swap_if_else(int cond, int x, int y) {
    int result;
    if (cond > 0) {
        result = x + y;
    } else {
        result = x - y;
    }
    return result;
}

__attribute__((noinline))
void take_int(int v) { g_sink = v; }   /* opaque noinline call */

__attribute__((noinline))
int spaghetti_pattern(int cond, int x) {
    if (cond) {
        /* volatile write + opaque call: two side effects the compiler
           cannot merge into one statement */
        g_sink = x * 2;
        take_int(x + 1);
    }
    return x;
}

/* --- Group 4: Negative offsets (CONTAINING_RECORD) --- */
struct Inner { int a; int b; };
struct Outer  { int header; char pad[4]; struct Inner inner; };  /* inner at offset 8 */

__attribute__((noinline))
void takes_inner_ptr(struct Inner* q) { g_sink = q->a; }

__attribute__((noinline))
void negative_offset_access(struct Inner* p) {
    /* p actually points at Outer.inner (offset 8) inside a larger
       allocation; code probes 8 elements past the end of Inner.
       NOTE: Hex-Rays scales p+N to N in cot_add numval, and folds
       p[N] to cot_idx — this call-arg form is the only shape that
       survives as cot_add(var, num). */
    takes_inner_ptr(p + 8);
}

/* --- main: force linker to keep all functions --- */
int main(void) {
    struct ScanTarget st = {0};
    scan_simple(&st);
    scan_chain(&st);
    rename_assign_chain(1, 2);
    rename_call_arg(3);
    g_sink = swap_if_else(1, 2, 3);
    g_sink = spaghetti_pattern(1, 4);
    struct Outer outer = {0};
    negative_offset_access(&outer.inner);
    return g_sink;
}
