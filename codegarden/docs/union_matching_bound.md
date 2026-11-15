# Exact union search and a cheap residual bound

Let U be the union of two valid codes. The common words are isolated within U; the two exclusive parts form a bipartite conflict graph. For a selected set T of outside words, let B(T) be all union words sharing a distinct two-deletion descendant with any member of T. An exact maximum matching gives alpha(U minus B(T)) by Konig's theorem. A valid completion exists exactly when T itself is valid and that independent-set size plus |T| reaches the target.

For any fixed matching M in U, its edges with neither endpoint removed remain a matching after deleting B. If h(B) counts matching edges touched by B, then

alpha(U minus B) <= |U| - |B| - |M| + h(B).

When M is maximum, the right side is alpha(U) - |B| + h(B). The optimized kernel precomputes each outside word's union blocker mask and touched-matching mask, then combines them by bitwise OR. If this upper bound plus the allowed outside-word count is below227, it skips an unnecessary exact matching calculation. This is a mathematical upper bound, not a heuristic deletion of candidates.

The new kernel retains exact matching for surviving queries. Brute-force tests check the matching result and the bound on small bipartite vertex-deletion fixtures. A resumed search recomputes the eligible pool and checks its complete ordering against the old source-pinned report before skipping a completed root prefix. The interrupted active root is retried; completed roots are not re-run. Timeouts remain open.

Relevant source: `phase3/union_external3.cpp::Research::alpha`, `Research::dfs` and `Research::run`. Its explicit query pools and root counts define local families, never a global optimum. Source2's600-second deadline was soft and actual601–608CPU seconds were reported. The new inner-loop deadline polling reduces that overrun.

`phase3/bench_union_bound.py` compares old/new kernels on identical already-closed five-outside-word fixtures, with matching candidate ordering and actual CPU/wall measurements. This is a correctness/performance regression study, not a new code or held-out trained-policy evaluation.
