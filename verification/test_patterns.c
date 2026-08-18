#include <stdint.h>
#include <stdlib.h>

/* anti-dead-code sink: defined here (not just `extern`) so the linker
   has a symbol to resolve. `volatile` forces every read/write to hit
   memory, defeating any residual optimizer cleverness at -O0. */
volatile int g_sink = 0;

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

/* --- Group 2: Rename (assignment chains + call args) --- */
__attribute__((noinline))
void rename_assign_chain(int real_name, int a2) {
    int a1 = a2;                  /* RenameOther target: a1 <- a2 */
    g_sink = a1 + real_name;
}

__attribute__((noinline))
void callee_takes_arg(int meaningful) {
    g_sink = meaningful;
}

__attribute__((noinline))
void rename_call_arg(int real_value) {
    int a1 = real_value;
    callee_takes_arg(a1);         /* RenameOutside target: a1 <- "meaningful" */
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
int spaghetti_pattern(int cond, int x) {
    if (cond) {
        x = x * 2;
        x = x + 1;
    }
    return x;
}

/* --- Group 4: Negative offsets (CONTAINING_RECORD) --- */
struct Inner { int a; int b; };
struct Outer  { int header; char pad[4]; struct Inner inner; };  /* inner at offset 8 */

__attribute__((noinline))
void negative_offset_access(struct Inner* p) {
    p->a = 1;
    p->b = 2;
    g_sink = p->a;
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
