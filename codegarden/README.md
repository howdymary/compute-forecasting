# CodeGarden

Auditable search for binary two-deletion-correcting codes of length 16.
**Current verified best: 226, reproduced from kgrey's arena submission 2778.
No improvement or new global record is claimed.**

All application files, environments, outputs and documentation live in codegarden/.
The sole approved exception is .github/workflows/codegarden.yml, the isolated
remote launcher. Development is on the codegarden branch. Existing forecasting
source, dependencies, Modal apps/Volumes and workflows are untouched.

## Reproduce without a workstation checkout

Open the CodeGarden GitHub Actions run on the codegarden branch:
https://github.com/howdymary/compute-forecasting/actions

The launcher fetches an immutable commit on a standard public GitHub-hosted Linux
runner, creates codegarden/.venv, verifies, searches, verifies again and commits
allowlisted outputs back with a branch lease. It never force-pushes or cancels
another project's job. To launch a changed bounded batch, commit a reviewed
change to the isolated launcher on codegarden. Do not edit an existing
forecasting workflow. No private account balance or credential is published.

For execution in an authorized remote container, from the repository root:

~~~sh
python -B -m unittest discover -s codegarden/tests -v
python -B codegarden/protected/verify_descendants.py codegarden/artifacts/best_code.txt
python -B codegarden/protected/verify_lcs.py codegarden/artifacts/best_code.txt
python -B codegarden/supervisor.py codegarden/artifacts/best_code.txt
python -B codegarden/search.py --start codegarden/artifacts/best_code.txt --seconds 60 --cycles 1000 --seed 17 --policy adaptive --output codegarden/artifacts/new_run.json
python -B codegarden/supervisor.py codegarden/artifacts/new_run.txt
~~~

Plain witnesses are one exactly 16-bit word per line. Both independent verifiers
also accept a JSON list or the official {"words": [...]} object. Both reject
duplicates, malformed words, and empty input. The descendant verifier returns
conflicting words, a shared descendant and deletion positions on failure.

## Exact repairs

Optional dependency in the isolated environment: ortools==9.14.6206.

~~~sh
codegarden/.venv/bin/python codegarden/cp_sat.py --start codegarden/artifacts/best_code.txt --seconds 20 --seed 17
codegarden/.venv/bin/python codegarden/cp_sat.py --start codegarden/artifacts/best_code.txt --global-pool --seconds 300 --seed 29 --output codegarden/artifacts/global_cp.json
~~~

CP-SAT uses sparse descendant occupancy, not a dense conflict graph. A feasible
output must pass the independent verifiers. INFEASIBLE concerns the explicitly
encoded pool and fixed outside. UNKNOWN is not an impossibility proof.

The Python bounded branch-and-bound and bipartite-union repair need no external
packages. Union certificates contain a matching and minimum vertex cover.
They prove the optimum in that union only.

## Inspect logs

~~~sh
python -B codegarden/read_log.py codegarden/logs/pilot_001.json.zlib
~~~

Each exact neighborhood records the starting witness hash, full fixed outside,
candidate pool/hash, restrictions, target and solver status. The plain
remote_run.json is the completed CPU run; later batches retain separate receipts.
No timeout is promoted to an optimality claim.

## Demo

Serve codegarden/demo in a remote container:
python -m http.server 8000 --directory codegarden/demo

The browser displays actual recorded scores, witness download, source links,
verification output, a live unique-deletion decoder, and a rejected candidate.
It labels recorded runs and unexecuted sponsor integrations explicitly.

## Sponsor integration and budget boundary

budget/ledger.py is an atomic accounting implementation, not an assertion that
all projects currently participate. A production deployment must use ONE shared
transactional coordinator with verified balances and other projects' pending
reservations. Unknown/stale values fail closed. It reserves verification budget.

- integrations/exa.py::search_methods is the real Exa request implementation.
- integrations/past_memory.py namespaces real researcher/strategist/analyst
  authors, validates actual recalled source IDs, and logs causal references.
- integrations/modal_workers.py provides isolated CPU workers and durable volume
  artifacts; no existing app or volume is stopped.
- integrations/tinker_policy.py implements bounded strategy choices and
  verifier-grounded SFT. Untrained/trained held-out evaluation is mandatory before
  claiming adaptation gains.

An adapter's existence is not evidence of execution. See integrations/STATUS.md
and artifacts/tinker_evaluation.json for current live status. The local adaptive
controller is empirical UCB, not an LLM and not a Tinker-trained policy.

## Scope and credit

Arena: https://einsteinarena.com/problems/two-deletion-code-16
CPro1: https://github.com/Constructive-Codes/CPro1
Weindel–Heckel: https://arxiv.org/html/2504.00613v2

The 208-word CPro1 result is pinned to commit
5b26b1a5ca0625a857cf6c2adcc6668e1d66a2ac and matches the downloaded arena baseline.
The 215 result is a literature report; it is not presented as a reproduced
witness. The 226 arena witness is independently reproduced. Literature coverage
does not establish a complete global-record audit.
