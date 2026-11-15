# CodeGarden Kakeya pilot

This isolated pilot targets EinsteinArena's [128-triangle Kakeya problem](https://einsteinarena.com/problems/kakeya-needle-128). It preserves all deletion-code sources, witnesses and verifiers. No227-word deletion code was found.

The reproduced leader is kgrey solution2772, exact area approximately0.10675138995168142. See `provenance.json` for the full rational value and witness/verifier hashes. This is a reproduction, not a new record.

Two standard-library exact checkers certify JSON witnesses of128 decimal strings: the pinned official endpoint-trapezoid implementation and a separate midpoint integrator. Run them together with:

```sh
python3 -B codegarden/kakeya/verify.py codegarden/kakeya/baseline.json
python3 -B codegarden/kakeya/protected/independent.py codegarden/kakeya/baseline.json
```

The floating C++ area/gradient kernel is only a proposal engine. Independent exact small-instance comparisons, finite differences and baseline certification gate remote searches. At ties, the kernel supplies a deterministic one-sided gradient choice. Search heuristics cannot redefine acceptance.

The dedicated branch launcher compiles and tests on GitHub Actions, then runs matched coordinate-versus-structural basin-hopping searches on Modal. Native code is compiled inside the Modal image to avoid host ABI mismatches. Dependencies stay in an isolated environment. All source and runtime artifacts remain under codegarden, except the authorized GitHub launcher.

The initial pilot deadline is22:35:18 UTC on15November2026. No new provider work may launch after that deadline without a new decision based on results. An unchanged best score is not progress toward a record. Results must distinguish numerical proposals, exact improvements, Arena improvements, and literature-audited global claims.

Exa provenance, bounded Tinker parameter decisions and past.dev handles are recorded in runtime artifacts. Witnesses and experiments in GitHub/Modal durable storage remain authoritative. No provider balances are queried and no new purchases are authorized.
