# Paired blocker-closure-guided repair

Best verified cardinality remains 226. These are bounded exploratory experiments; no new construction is claimed.

## Decision and measurement

The previous 96 mandatory-pivot queries with randomly enlarged removal sets all finished without a 227-word code. To test whether unstructured removals produced poor repair opportunities, this experiment pairs six fixed pivots and removal sizes 32 and 64 with two strategies: random removal and greedy blocker closure. The same 0.25-second clique-search cap applies to each explicit model.

For guided removal, group compatible outside candidates by their missing incumbent blockers. Choose the group maximizing (candidate count + 0.15 * existing-overlap sum) / additional blockers, then remove those blockers. Only candidates with at most four original blockers drive this heuristic. The final exact repair pool nevertheless contains EVERY length-16 word compatible with the fixed outside code and mandatory pivot, with no four-blocker restriction.

At removal size 32 the random pools had 30–36 candidates; guided pools had 662–913. All 12 guided queries timed out at the initial cap. Of 12 random queries, 11 completed and one timed out. These results demonstrate different model sizes and search difficulty, not improved construction quality.

The timeouts led to a second implementation with Uint32 bitsets in Node. It independently reconstructs each pool from descendant ownership and checks that its full SHA-256 matches the Python model. It searches two 32-removal guided pools with a five-second cap:

- Pivot zero, 662 candidates: completed after 376,301 nodes, approximately 3.27 seconds, without a 227-word code.
- Pivot one, 779 candidates: timed out after approximately five seconds, without a feasible improvement. This query remains open.

Across the original 24 models, 12 are now completed scoped negatives and 12 remain open. No claim covers another pivot, another removal set, or another code. Neither a formal absence certificate nor global optimality is claimed.

## Reproduction in an authorized ephemeral environment

`python3 -B codegarden/artifacts/side_research/2026-11-15-guided-pivots/guided_search.py`

`node codegarden/artifacts/side_research/2026-11-15-guided-pivots/uint32_probe.mjs`

Only Python standard-library and Node built-in dependencies are used. Both retrieve the immutable seed and verify SHA-256 before searching. No files are generated and no paid API is called. Python has a 45-second CPU limit and a 32-second experiment cutoff; each initial exact query has a 0.25-second wall cap. Node has two five-second search caps plus finite preprocessing. Timing and timeout node counts depend on the machine.

The Python routine passed nine brute-enumerated graph fixtures; the Node routine passed 44, testing both feasible-optimum and infeasible-above-optimum targets. These are correctness checks on small graphs, not independent formal verification of the larger absence results. Both retained the seed code, with 6,410 distinct descendants and maximum pairwise LCS 13. The project's protected verifier-only gate remains mandatory for any future claimed improvement.

All four original evidence files and the main branch are preserved. This revision adds only these five evidence files, without workflow, verifier, provider, billing, other-project or running-job changes.
