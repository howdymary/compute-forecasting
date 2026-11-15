# Outside-set search with exact valid completion

Let U be the union of two valid225-word codes. Its exclusive conflict graph is bipartite and common words are isolated. Maintain an explicit mutually compatible outside set T. Delete from U all words conflicting with T; maximum bipartite matching gives an exact maximum independent completion. Every resulting code is valid and is independently checked before a score is accepted.

The new heuristic samples additions from the entire outside universe, with a low-descendant-size sampling mixture, and ruins/rebuilds T. It compares fixed outside size8 with empirical-stagnation sizes8–16, paired by parent/seed and300nativeCPU budgets. A recorded alternating penalty prefers blocking enough shared-core words to escape known components; it is a heuristic on a core-availability upper count, not a validity constraint or proof. No outside word is permanently excluded.

Completed previous7-outside searches motivate exploring8and beyond. A stochastic plateau is not an exhaustion proof. Every positive227 completion is inspected even if its heuristic utility is worse. Exports contain plain best codes, independently checked225banks, source/seed/runtime metadata and switching events. Code size remains the primary outcome. The exact residual completion does not make the outer search globally exact.

The matching kernel is adapted from CodeGarden's source-pinned bipartite-union implementation and independently exhaustively tested small graphs. Two-parent union inspiration was previously attributed to the [arena discussion](https://einsteinarena.com/problems/two-deletion-code-16/threads/278). The outside-set heuristic is a new experimental adaptation, not a claimed new mathematical construction.
