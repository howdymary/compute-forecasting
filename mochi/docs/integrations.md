# Capability inventory · November 15, 2026

The existing checkout contains Git metadata only, with an unborn `metagame`
branch. Remote `origin/compute-observatory` was fetched for read-only source
inspection. No reset, branch switch, parent source edits or archive changes.

| Capability | Local | Existing remote path | Mochi use |
|---|---|---|---|
| GitHub | Authenticated `gh`; credential values not read | Repo Actions | Separate `mochi-research.yml` and branch |
| Blender | 5.1.2 installed | Not needed for numerical experiment | Local recorded-transform rendering |
| MuJoCo | Installed in `mochi/.venv` | Independent pinned image | Original supported humanoid contact simulation |
| Exa | No API key in environment | `EXA_API_KEY` secret name confirmed | Failure-specific search in main loop |
| past.dev | No API key in environment | `PAST_API_KEY` secret name confirmed | Four authors, verified source IDs, explicit audiences |
| Tinker | No API key in environment | `TINKER_API_KEY` secret name confirmed | Bounded Qwen decisions; no new training |
| Modal | No token variables in environment | Both Modal secret names confirmed | Separate `mochi-robot-lab`, <=8 CPU workers |

Parent patterns inspected: `docs/past-dev-memory.md`,
`src/compute_forecast/memory_value_v5.py`, and
`.github/workflows/value-memory-v5.yml` at the fetched remote revision.
The parent module imports and initializes a Modal application at module scope;
Mochi uses small independent adapters instead of importing that module.

The adapters preserve the parent's verified-source-ID / exact numerical payload
pattern. A missing recall fails the live run; it never counts a fallback as
successful sponsor use. Author/audience identifiers are short, namespaced, and
unique per run. No forecasting checkpoint, audience or storage is reused.

Mochi is its own package. The only root-level addition is an additive Actions
workflow. It references existing secrets; those values stay on the runner.
No forecasting deployment or billing configuration is changed.

## Executed verification

Successful workflow: https://github.com/howdymary/compute-forecasting/actions/runs/43762703104
Four model-driven roles, two Exa searches, eleven verified cross-role recalls,
one passed private-canary boundary, and 188 Modal rollouts completed. The public
replay site has its own app, `mochi-policy-studio`, with no provider secrets
attached. Previous bootstrap attempts failed on image-layer ordering and an
automatically uploaded package's protocol path. The successful image sets
`MOCHI_ROOT=/app` explicitly. Failed attempts are not counted as successful
sponsor runs. The remote default branch was reverified as `compute-observatory`;
the active local unborn `metagame` branch was preserved.
