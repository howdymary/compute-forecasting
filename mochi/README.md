# Mochi · A tiny robot with a scientific method

An original supported humanoid pushes a star-stamped puck into a target. A
bounded research loop diagnoses failures, searches Exa, proposes controller
changes, evaluates them on Modal, and shares evidence through past.dev. A critic
and deterministic gate decide which changes survive. Blender and the browser
replay actual MuJoCo body trajectories.

This is an independent Track 5 subproject. The forecasting application, its
archives, deployment, model weights and benchmark inputs are unchanged.

**[Open the Mochi studio](https://howdymary--mochi-policy-studio-web.us-east.modal.run)** ·
**[Two-minute demo](https://howdymary--mochi-policy-studio-web.us-east.modal.run/data/demo.mp4)** ·
**[Executed research and limits](docs/results.md)** ·
**[Successful sponsor workflow](https://github.com/howdymary/compute-forecasting/actions/runs/43762703104)**

The live study completed 188 Modal rollouts, two Exa searches, nine Tinker
decisions, and eleven verified cross-agent past.dev recalls. Held-out success
was 8/12 for the research-selected controller versus 2/12 initially and 6/12 for
the conventional control. Under higher friction and mass it fell to **1/8**,
versus 6/8 for conventional search. This is conditional improvement and an
important generalization failure, not a universal win or proof of search value.

## Desk humanoid design and expanded study

[Design 02 preview](https://howdymary--mochi-policy-studio-web.us-east.modal.run/concept.html) gives Mochi a compact mechanical humanoid body on a full-size desk. [The design notes](docs/desk-humanoid.md) distinguish its static Blender rig and proposed desktop-bowling task from the measured supported-pushing simulator.

The separately registered robustness follow-up uses eight research rounds, the same controller-family access in both search arms, fresh friction/mass mixtures, and a maximum of 2,016 Modal simulations. Execution: [workflow 43765530700](https://github.com/howdymary/compute-forecasting/actions/runs/43765530700). Do not pool its outcomes with V1.

## First visible slice

- Original procedural mini humanoid and tabletop scene.
- Three-joint actuated right arm; state-based control, fixed supported base.
- Real contact dynamics in MuJoCo 3.3.7.
- Frozen starting policy and reproducible parameter search.
- Before/after viewer with a shared playback clock and held-out replay.
- Blender scene generation, film encoding, source and memory evidence panels.

Current runtime status and numerical outcomes are in `web/data/report.json`
when a demo pack has been published. A local conventional-search run is never
presented as a successful sponsor-connected run.

## Run locally

From the repository root, using Python 3.11:

```sh
uv venv mochi/.venv --python 3.11
uv pip install --python mochi/.venv/bin/python './mochi[dev]'
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.cli capabilities
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest mochi/tests -q
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.cli demo --out mochi/artifacts/local
mochi/.venv/bin/python mochi/scripts/publish_local.py mochi/artifacts/local
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.cli serve --port 8765
```

Open http://127.0.0.1:8765. `PYTHONPATH` explicitly points at the live source
tree; the Python package can also be installed non-editably. Current commands
assume a repository checkout because the fixed protocol and web assets are kept
in the independent subproject. Set `MOCHI_ROOT` to its absolute path if needed.
The Three.js viewer and optional fonts use public CDNs and need network access.

## Render the recorded motion

Blender 5.1.2 was used locally. Run a smoke render first:

```sh
blender --background --python mochi/scripts/blender_scene.py -- --trajectory mochi/artifacts/local/selected.json --out mochi/artifacts/preview --still --width 960
```

For each of `baseline`, `selected`, and `heldout`:

```sh
blender --background --python mochi/scripts/blender_scene.py -- --trajectory mochi/artifacts/local/selected.json --out mochi/artifacts/film-selected --stride 2 --width 960
mochi/.venv/bin/python mochi/scripts/encode.py --root mochi/artifacts --scope local --stride 2
mochi/.venv/bin/python mochi/scripts/publish_local.py mochi/artifacts/local
```

The transform exporter is deliberately simple: body positions and quaternions
are sampled at 25 Hz; Blender keyframes selected samples and renders those
frames. `stride=2` is encoded at 12.5 FPS, preserving six seconds of real time.
Generated `.blend` scenes and large frame sequences stay ignored; short public
renders may be published in a release/demo pack with source hashes.

## Sponsor-connected execution

The parent repository's GitHub Actions secret names are reused by the additive
`.github/workflows/mochi-research.yml` workflow. No keys were copied locally.
The existing `metagame` checkout remains unchanged; code is prepared on the
separate `mochi-hackathon` remote branch.

The workflow installs `mochi[remote,dev]`, runs tests, then runs:

```sh
python -m mochi.research --out mochi/artifacts/live
```

Required server-side variables: `EXA_API_KEY`, `PAST_API_KEY`, `TINKER_API_KEY`,
`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`. The separate Modal app is
`mochi-robot-lab`, with at most eight one-CPU / 1 GiB workers and 180-second
function timeouts. The research loop is bounded to two rounds and 48 candidate
rollouts, plus baseline, matched control, and final evaluations.

Download the workflow artifact, inspect `live/report.json`, and publish that
folder using `scripts/publish_local.py`. The local preview and live study have
different candidate budgets; keep their claims separate.

The published pack can be audited without provider credentials:

```sh
mochi/.venv/bin/python mochi/scripts/audit_pack.py mochi/web/data
```

This checks exact numerical summaries, four model-driven roles, eleven consumed
cross-agent records and their payload hashes, matched simulation counts, provider
receipts, the preserved robustness failure, and all thirteen artifact checksums.
The final Blender audit checked fourteen body poses at three recorded keyframes,
with maximum component error below 3e-8. The 120-second MP4 uses measured study
results and the corresponding recorded Linux trajectories.

Exact integration locations:
- `src/mochi/integrations.py`: Exa search, past.dev writes/recalls, bounded
  Tinker/Qwen decisions. No import-time network calls.
- `src/mochi/research.py`: failure-driven source-to-experiment loop, rejection
  decisions, equal-budget control, selection freeze and final evaluation.
- `src/mochi/remote.py`: asynchronous Modal fan-out, actual resource receipts.
- `configs/protocol.json`: fixed evaluation contract and disjoint seed sets.
- `docs/integrations.md`: local/remote capabilities and parent-pattern reuse.

## past.dev challenge

### Agents

Four model-driven roles use the same Qwen/Qwen3.5-4B base sampler with different
instructions, bounded choices, identities and contexts. Researcher writes sourced
mechanisms and reads criticism. Designer reads research and writes proposals.
Experimenter reads proposals, selects a diagnostic, executes the fixed numerical
tool and writes results. Critic reads results/evidence and writes a verdict.
The researcher consumes that verdict before the next query.

All writes have timestamps, authors and explicit audiences. A shared Mochi
audience connects the roles; a critic-only audience holds a synthetic canary.
The researcher must not retrieve that private source. IDs are unique per run
and stay within the documented audience length constraints.

### Layers

Working context is per-role. Past.dev holds authored episodic events and their
semantic evidence. Versioned Python holds procedural methods. Exact numerical
payloads and trajectories live in JSON artifacts. A recall must return the
required source ID; only then is the exact canonical payload supplied to the
consumer. No fallback is counted as successful recall.

### Results

Executed results, source IDs, hashes, reader/writer identities, model decisions,
ingestion completion, and write-to-readable latency are retained in each live
report. The service-connected run must finish before eligibility is claimed.
Local conventional search proves only the simulator/evaluator/rendering slice.
No benefit from memory or search is inferred merely from calling the APIs.
The successful study has four writers/readers, eleven cross-agent recalls, and
a passed positive/negative private-canary check. See `docs/results.md` and the
versioned report for actual decisions and the robustness failure.

### Caveats

This is a small constrained manipulation study. Roles select registered actions
and policy families; they do not invent arbitrary new control code. Search
sources motivate a choice among supported families. There is no matched
no-memory or no-search ablation yet, so their causal benefit is unproven. The
random-search comparison matches simulation counts, not total model cost.
It also uses a narrower open-loop family than the research arm, which can
choose feedback; this confound prevents attributing the difference to Exa.
Private-reader isolation is one positive/negative synthetic canary check, not
an exhaustive security audit. Prior hypotheses are qualified by later authored
critic conclusions; native semantic supersession is not assumed or proven.

## Evaluation and limitations

See [architecture](docs/architecture.md) and the fixed protocol. Selection uses
development success count, then mean final distance. Held-out and higher-friction
/ higher-mass scenarios run only after the selected policy is frozen. Report
Wilson intervals and all paired trials. The showcase seed is selected on
development for a visible baseline failure, and labeled accordingly.

Only the hand collides with the puck/table; other arm and self collisions are
disabled. The robot is supported and the legs are cosmetic. Obstacles, vision,
walking, neural training, contact-force safety validation and sim-to-real
transfer are outside this slice. The control model is deliberately simplified.
Successful table-boundary checks are not a safety certification.

## Reuse and provenance

Mochi's robot, scene, task, controller, evaluator, UI and renderer were created
on November 15, 2026. Parent service patterns were inspected and adapted without
importing forecasting jobs. Attribution: MuJoCo (Apache-2.0), NumPy (BSD-3-Clause),
Three.js (MIT), Blender (GPL; output licensing separate), FastAPI (MIT), and the
respective Modal, Exa, past.dev and Tinker SDK/API terms. External research links
and short excerpts keep their source attribution. No external robot meshes or
forecast data were used. Protocol hashes accompany the numerical results.
