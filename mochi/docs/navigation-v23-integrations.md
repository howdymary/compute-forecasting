# Navigation study integrations

The active root checkout is the unborn `metagame` branch with an empty Git index. This study uses new files under `mochi/` and an isolated delivery index. Existing branches, checkpoints, archives and deployments are preserved. V22 established a small fixed-layout controller comparison, not layout generalization or native gait learning.

## Access and reuse

The authenticated Modal 1.6.4 CLI can execute new applications. Existing backend secrets `compute-forecast-signals-v6` and `compute-forecast-evidence-future-v15` supply the Tinker, Exa and past.dev environment variables. The access probe checked presence without printing values and confirmed Qwen3.5-4B availability through an actual Tinker capabilities request. No new credentials, frontend credentials or Actions secret changes are needed.

`src/mochi/navigation_v23/services.py` adapts the existing source-verified `ReviewServices` memory client and Exa search client. A new shared audience, a private critic audience, explicit reader identities, completed-ingestion polling and source-ID verification keep this study separate. The main campaign writes a private canary and verifies that an unauthorized reader cannot retrieve it. Semantic records are compact; exact trajectories and arrays live in the new Modal volume.

`src/mochi/navigation_v23/remote.py` defines a separate `mochi-navigation-v23` application and `mochi-navigation-v23-artifacts` volume. Four bounded CPU workers run the same evaluator as the local engineering probe. Each attempt saves its full trajectory, summary, resource receipt and public replay. The orchestrator and simulator use asynchronous Modal calls where appropriate. The final viewer receives no service secrets.

`src/mochi/navigation_v23/campaign.py` performs real Tinker forward/backward and optimizer steps on a fresh rank-16 Qwen3.5-4B navigation adapter. Parent and intermediate states are saved. The model selects one bounded clearance and walking-controller profile before each physical route; the native ONNX gait is unchanged. This distinction applies to every checkpoint comparison.

## Local and remote execution

Local execution covers scene validation, geometry-derived planning, the initial physical probes, artifact analysis and viewer development. Remote execution covers model inference and training, Exa queries, actual memory ingestion/recall, and parallel physics batches. Frozen final layout files are uploaded to the new experiment's volume namespace before checkpoint selection. Only the evaluation stage opens them.

From the repository root:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/modal run mochi/src/mochi/navigation_v23/remote.py::check_access
PYTHONPATH=mochi/src mochi/.venv/bin/modal deploy mochi/src/mochi/navigation_v23/remote.py
PYTHONPATH=mochi/src mochi/.venv/bin/modal run mochi/src/mochi/navigation_v23/remote.py::launch
```

The launch command refuses to overwrite an existing campaign. Inspect its saved progress before any continuation. Reproduction uses a new run identity and regenerated final set. The frozen protocol records episode, CPU, API, token and spending ceilings; consuming credits is not an objective.

The first orchestration attempt saved an untrained parent and completed real service handoffs, then stopped before any remote physical trial or optimizer update. Importing a second copy of the function-definition module produced an unbound Modal function. The repaired campaign uses deployed-name lookup. Its new identity preserves the interrupted records and conservatively carries their service usage and unused reservations. The physics, action contracts, layout splits and verifier were unchanged.
