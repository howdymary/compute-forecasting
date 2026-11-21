# Inkling 2 Mini found a clearance error in Mochi's route

Inkling 2 Mini reviewed measured MuJoCo failures, controller source, collision geometry and three recorded simulation images. Its accepted proposal changed one post-laptop waypoint. The robot moves farther clear of the laptop before turning toward the globe.

The change converted two fresh failures into qualified four-task completions. The reference completed zero of four fresh routes within the quality limits; the revised controller completed two. Both remaining failures occurred during laptop closing, before the changed waypoint was used. This is a specific controller-engineering improvement. It does not establish fewer steps, reliable laptop contact, better arm recovery or learned native locomotion.

[Inspect the continuous comparisons](https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run/) · [Protocol and selection history](inkling-v21-protocol.md) · [Machine-readable assessment](../evidence/inkling-v21/assessment.json)

## What the model actually did

Tinker sampled the published `thinkingmachines/Inkling-2-Mini` weights through the official `tml_v0` renderer. The backend first verified that the exact model was available to the account. There was no fallback to a different model.

The three image inputs came from the retained C19r1 development scenario 212000 at checkpoint 4, at 245, 258 and 271.5 physical seconds. They were cropped from the actual simulation replay, not generated as evidence. The model receipts retain their hashes. These previously observed images were development context, not unseen evaluation cases.

The model proposed bounded controller parameters. A typed interpreter rejected unsupported fields and applied permitted changes through existing actuator controllers. It could not modify task success, validity thresholds, physics, geometry, task order or recorded evidence. Generated source code was never executed.

This pilot made zero optimizer updates. Inkling's weights, Mochi's native ONNX gait and the original controller source remained fixed. Trials applied the declared parameter overrides. The selected route parameter changes an outer controller target, not a neural gait network. The separate C19r1 study completed eight real Qwen selector updates; those are not credited to Inkling.

## The failure and the change

After closing the laptop, the original route targeted `(0.320, 0.105)` metres before turning. The laptop-base collision box extends to y = 0.085 m. Despite the root reaching the nominal clearance pose, the ankle's swept geometry still contacted the base during departure. Root position alone was an inadequate clearance test.

After seeing the measured contact, failed proposals and actual collision bounds, Inkling proposed changing only the waypoint's y coordinate to 0.055 m. The selected configuration keeps the original x coordinate, task order, P5 laptop controller, W10 walking controller and R4 recovery controller. Motion still comes from simulated forces and contacts, with zero applied root force.

On development seed 221000, the reference stopped after 339 steps with an ankle/laptop-base collision. The proposal completed the uninterrupted clock, book turnaround and forward descent, drawer, laptop and globe sequence in 418 steps and 277.8 physical seconds. Development seed 221001 retained its laptop-closing failure.

The selected configuration and 239 source/configuration files were frozen before fresh seeds 223000 through 223003 were opened. The original 236 frozen files from C19r1 were unchanged. Restored-state component tests informed development; no restored branch is presented as a continuous demonstration.

## Fresh results

| Scenario | Reference | Clearance proposal |
| --- | --- | --- |
| 223000 | Laptop closing failed, 306 steps | Same failure, 306 steps |
| 223001 | Laptop closing failed, 292 steps | Same failure, 292 steps |
| 223002 | Ankle/laptop-base contact, 353 steps | Qualified completion, 444 steps |
| 223003 | Ankle/laptop-base contact, 351 steps | Qualified completion, 412 steps |

The two successful proposal runs took 279.9 and 275.1 physical seconds. Neither reference in those pairs completed. Comparing a successful full route with a failed partial route cannot establish a step, time or recovery-travel saving. There are zero pairs in which both sides qualified, so paired efficiency reductions are undefined. The declared target of four qualified completions and at least 10% fewer steps was not met.

The additional fixed P6 control qualified on seed 223000 in 428 steps and fell on seed 223001. That succeeds on one case where both primary P5 versions failed. P6 was not tested across all four cases or combined with the selected route in this frozen study. The two-case control cannot be pooled with or presented as a matched four-case cohort. The result supports testing arrival-dependent laptop controller choices in a subsequent study; it limits any claim that the accepted route is the best complete solution.

Four deterministic cases in one furnished desk layout are a small simulation pilot. They do not establish performance on another layout or real hardware. The default viewer scenario is the first fresh proposal recording that qualifies, not a randomly selected demonstration. All six development/fresh pairs remain selectable, including failures.

Descriptive 95% Wilson intervals for qualified completion are approximately 0–49% for the 0/4 primary reference and 15–85% for the 2/4 proposal. These broad intervals describe this small cohort and do not establish a population-level reliability claim.

## Rejected proposals

The first model call failed structured-output parsing. It remains a charged attempt, with a conservative token reservation; its unavailable output-token count is not reconstructed.

A final-review packet was rejected by the 24,000-input-token guard before model sampling. The compact retry kept the limit and physical evidence unchanged. In total there were six gateway invocations and five model-sampling attempts, with four parsed model outputs. The pre-sampling rejection is retained separately from model usage.

Zeroing terminal translation increased a matched laptop walking leg from 110 to 154 steps, including alignment increasing from 12 to 56. The proposal was rejected.

A revised laptop station with a declared 4 mm tracking window timed out after 367 alignment attempts without attempting the task. The additional tracking requirement was part of the implementation, so the failure cannot be attributed to the station coordinate alone. Subsequent proposals used an explicit tolerance no wider than the original 12 mm.

Starting alignment earlier kept 110 total steps and increased alignment steps from 12 to 15. Restoring the existing tolerance was excluded as a no-op. An initial closing-speed proposal misstated the commanded speed and was held for a factual error.

The existing P6 laptop controller fell on a hard development snapshot. Reducing P5's closing target to 0.30 rad/s failed on both tested snapshots. Neither contact proposal was promoted. Additional P6 controls were retained in the final study rather than dropping the alternative comparator.

## How the services were used

Modal hosted an authenticated research function with no public model endpoint. GitHub secret references supplied backend credentials. The separate public viewer serves recorded trajectories and evidence without making sponsor API calls. This pilot's physical experiments ran locally with bounded subprocess concurrency; earlier C19r1 physics ran on Modal.

Tinker provided actual Inkling inference with text and image inputs. Receipts retain model identity, execution source, input-image hashes, token counts, output hashes and structured proposals. The model never ran inside the high-frequency physics loop.

Exa performed two actual failure-driven searches. Sources were supplied as evidence for mechanisms to test. No no-search ablation was performed, so the study does not establish that search improved the result.

past.dev stored compact observations, sourced ideas, proposals and measured verdicts under four Mochi-specific identities. Writes were polled until ingestion completed. Dependent reads required the exact returned source ID before resolving canonical numerical content. The measured review recalled the earlier proposal before producing the accepted clearance change. A final review recalls the earlier findings and writes a qualified conclusion for the next cycle.

The completed memory record contains 12 writes, 17 logical recalls and 15 verified cross-role recalls. All four identities wrote and read, and no ingestion remains pending. The final verdict was ingested and recalled by the research identity. The Tinker token ledger totals 87,228 actual-or-reserved tokens across five sampling attempts; 23,793 of those are the retained conservative reservation for the first failed structured output.

The final model review correctly rejected step and arm-travel savings, but included an unsupported phrase describing P6 as a “2/4 hypothesis.” The actual P6 result is 1/2 on two explicitly reported controls. The raw model output is retained; deterministic measurements and the result table take precedence over that wording.

The shared and critic-private audiences are configured separately. This pilot did not run a new private-audience canary, so it does not claim a new isolation test. Recalls can include other authorized public sources; only the requested, verified Mochi record is supplied to the model. Public evidence omits unrelated source IDs. No memory ablation establishes a performance benefit.

The physical ledger accounts for 24 attempts and 5,002.38 summed single-thread wall seconds, or 1.390 hours, within its three-hour budget. This is conservative simulation resource accounting, not a provider invoice. The token ledger includes actual counts when available and the conservative reservation for the first failed structured output. Failed calls and experiments were not removed from the totals.

## Reproduction and inspection

From the repository root, use the existing Mochi Python environment and dependencies. The evaluation runner checks the frozen configuration before opening the specified cases. Existing attempt IDs are immutable; it will not silently overwrite an archived run.

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/reproduce_inkling_v21.py --run independent-check \
  --id independent-reference-223002 --mode full --seed 223002
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/reproduce_inkling_v21.py --run independent-check \
  --id independent-clearance-223002 --mode full --seed 223002 \
  --candidate mochi/configs/inkling-v21-selected.json
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_inkling_v21.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_inkling_v21_demo.py
```

The reproduction wrapper verifies the 239 frozen hashes and uses a separate named ledger under `mochi/artifacts/inkling-v21-reproduction/`. It preserves the 24-attempt, three-hour ceiling and the archived campaign ledger. The numerical audit requires the retained original raw artifacts under `mochi/artifacts/inkling-v21/`; it does not consume the independent reproduction files. Public replay clips and their hashes are available in the viewer manifest. Credentials and canonical backend artifacts are not embedded in the frontend.

The next physical bottleneck is laptop closing from the actual arrival states that still fail. The clearance change should be retained while contact proposals are tested in a new development cohort. New weight training needs validated action differences and a new frozen evaluation; this pilot supplies useful evidence, not a claim that more training already happened.
