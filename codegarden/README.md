# CodeGarden

**Best independently verified: 226 words, reproduced from the arena. No 227 found.**

[Current research status](docs/phase3_progress.md) · [Phase-two report](docs/phase2_report.md) · [phase-one report](docs/research_report.md) ·
[explicit witness](artifacts/best_code.txt) · [published replay](https://raw.githack.com/howdymary/compute-forecasting/21fc929ebc97258e7b76fb51a5dabeb3901eb389/codegarden/demo/index.html) ·
[final verification](artifacts/final_verification.json)

The bounded phase-two campaign added sparse compiled exchanges, population archives,
larger repairs, explicit exhaustion memory, and controlled proposer/memory evaluations.
All 1→2 through 4→5 direct exchanges around the pinned incumbent were enumerated without
improvement. All 512 selected larger repair pools were independently checked. These are
local results, not global optimality.

No new fine-tuning ran: all observed training gains only recovered known parent sizes.
The historical trained checkpoint and negative matched-CPU results are preserved.
See the report and artifacts for completed conditions, costs, limitations and source revisions.

## Remote execution

All project work is on the `codegarden` branch of
[howdymary/compute-forecasting](https://github.com/howdymary/compute-forecasting/tree/codegarden/codegarden).
Use the isolated [GitHub Actions launcher](https://github.com/howdymary/compute-forecasting/actions/workflows/codegarden.yml)
or an authorized remote container. No workstation checkout is required.
The launcher defaults to verification. Paid campaign code refuses new reservations after its
recorded cutoff; running a later paid campaign requires a refreshed shared allocation.
Do not reuse an expired budget snapshot or duplicate cumulative provider caps.

All project files, environments, caches, logs and dependencies stay under codegarden/.
The only exception is the approved `.github/workflows/codegarden.yml`.
BoundForge and forecasting files, dependencies, credentials, apps and jobs remain separate.

## Independent verification

Run from the repository root in the remote environment:

~~~sh
python -B codegarden/protected/verify_descendants.py codegarden/artifacts/best_code.txt
python -B codegarden/protected/verify_lcs.py codegarden/artifacts/best_code.txt
python -B codegarden/supervisor.py codegarden/artifacts/best_code.txt
python -B -m unittest discover -s codegarden/tests -v
~~~

The witness is plain data: exactly one unique 16-bit binary string per line.
The first verifier deduplicates descendants within a word and detects cross-word collisions.
The second uses independent pairwise LCS dynamic programming. Neither requires external
services, a model or search history. Their manifest and acceptance rules are unchanged.

## Native search and exact scoped audits

~~~sh
mkdir -p codegarden/.build
g++ -O3 -std=c++17 codegarden/phase2/kernel_v2.cpp -o codegarden/.build/kernel_v2
python -B codegarden/phase2/test_exchange.py
codegarden/.build/kernel_v2 30 17 adaptive codegarden/artifacts/checkpoint.txt 227 0 < codegarden/artifacts/best_code.txt
python -B codegarden/phase2/audit_certificates.py
python -B codegarden/phase2/exhaustion_index.py
~~~

The native program prints a candidate and an unverified score; export its `best` array
as 16-bit words and pass the result to the supervisor before accepting it.
Full search universe: 65,536 words; no dense conflict graph is required.
Exact repair audit imports no search or CP-SAT code and reconstructs every compatible pool.

Optional isolated dependencies:

~~~sh
python -m venv codegarden/.venv
codegarden/.venv/bin/python -m pip install -r codegarden/requirements-providers.txt -r codegarden/requirements-exact.txt -r codegarden/requirements-report.txt
~~~

Provider integrations are optional for verification. Runnable campaign entry points:
`phase2/campaign.py`, `phase2/supplement.py`, and individual exploratory probes.
Campaign publishers use branch leases and are intentionally tied to their documented
remote run/branch. Inspect the source and refresh run configuration before a future campaign.

## Evidence

- `artifacts/phase2/`: frozen cases, checked witnesses, operator receipts, memory role traces,
  scoped negatives, independent audit, duplicate configuration audit, figures and raw CSV.
- `budget/phase2-usage-summary.json`: cumulative conservative holds, account receipts and
  unresolved attribution; reservations are not charges.
- `demo/`: recorded research replay plus a live in-browser two-deletion decoder and rejected
  collision example. Serve this directory over HTTP, or use the commit-pinned published demo.
- `docs/phase2_report.md`: mathematical result, comparisons, sponsor evidence and gaps.

Protected source SHA-256 checks precede acceptance. Complement/reversal are the only
symmetries used; orbit probes checked their deletion-descendant preservation on all words.
Timeouts remain unknown; cached negatives require exact matching scope.

## Current adaptive research

The [current phase-three report](docs/phase3_progress.md) distinguishes completed local
results, open neighborhoods, actual provider evidence and the still-open227 objective.
The active strategy expands a fixed-core repair only after CP-SAT closes its novelty
model at225. A timeout remains open. Search goals can reject known226 arrays; code
validity remains the unchanged descendant/LCS specification.

For an authorized **remote** checkout with the committed parent artifacts:

~~~sh
python3.11 -m venv codegarden/.venv
codegarden/.venv/bin/python -m pip install ortools==9.14.6206
mkdir -p codegarden/.build
g++ -O3 -std=c++17 codegarden/phase3/bundle_guard.cpp -o codegarden/.build/bundle
export GITHUB_SHA=$(git rev-parse HEAD)
codegarden/.venv/bin/python -B codegarden/phase3/adaptive_hulls.py --prepare
codegarden/.venv/bin/python -B codegarden/phase3/adaptive_hulls.py --case 0
~~~

Cases0–7 compare paired random-one/adaptive-unlock relaxations from four frozen225
parents. Each search batch targets600wall seconds with two solver threads; verification
and successful-code augmentation add bounded overhead. To continue an interrupted225
checkpoint with the same engine, add `--resume`. Checkpoint source/engine hashes,
explicit candidate pools, negative scopes and independently accepted witnesses live
under `artifacts/phase3/adaptive_hulls_001/`.

These commands make no Exa, past.dev, Tinker or Modal calls. A new paid campaign must
refresh the shared allocation; all unresolved holds and other-project reserves remain
in force. Standalone witness verification needs no optional packages or providers.
