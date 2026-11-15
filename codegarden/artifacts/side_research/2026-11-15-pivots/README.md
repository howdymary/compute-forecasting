# Side investigation: forced-pivot repair and execution diagnosis

This evidence branch is separate from the main CodeGarden branch. Best remains the reproduced 226-word code. No 227-word code was found.

## Exact repair experiment

Run `python3 -B codegarden/artifacts/side_research/2026-11-15-pivots/pivot_search.py` in an authorized ephemeral research environment. It uses only the Python standard library, retrieves an immutable seed witness and verifies its SHA-256 before search. It creates no files and uses no paid API. CPU time is limited to 45 seconds; individual encoded repair searches have a 0.12-second observation budget.

Seed: 2271129. Nine independently brute-enumerated small graph fixtures validate the clique routine. For each of 96 query definitions, the forced outside word has 2–8 distinct incumbent blockers. The removed incumbent set has size 12, 16, 24, 32, 48 or 64. The repair pool includes every one of the 65,536 words compatible with the fixed outside code and mandatory pivot. Its literal pool hash and removed incumbent indices are in results.json.

With r incumbent words removed and one mandatory pivot added, r further words are required for a 227-word construction. A greedy-coloring upper bound and bitset clique search finished all 96 encoded queries without one. Many finish at the root bound. This is not an exhaustive search over removal sets, pivots, all exchanges, or all codes. There is no independently checked formal absence certificate.

The frozen-seed replay reproduced every query definition, pool hash and result exactly. Final checks independently generated string descendants and pairwise dynamic-programming LCS values; the retained seed has 226 words, 6,410 distinct descendants and maximum LCS 13. These exploratory checks do not replace the project's protected verifier-only acceptance gate.

## KaMIS execution diagnosis

kamis_diagnosis.json distinguishes five SIGILL process failures from mathematical negatives. The CPU-portability explanation is a hypothesis supported by the host-specific build flag and cross-runner binary reuse. It is not proven without CPU feature and crash evidence. The recommended portable rebuild has not been launched or applied.

No workflows, main-branch files, protected checkers, provider allocations, billing settings, other projects or running jobs were changed. There were no sponsor calls in this side investigation.
