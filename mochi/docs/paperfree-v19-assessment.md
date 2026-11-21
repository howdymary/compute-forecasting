# Paper-free desk: step-first controller post-training

The paper-free study completed eight Tinker optimizer updates. Development selected update 1. On four fresh scenarios, the selected model completed two routes within every quality limit; the parent completed none within those limits. This is a small observed completion difference. It does not establish a reliable step reduction. The declared target was not met.

[Continuous recordings](https://howdymary--mochi-paperfree-v19-demo-web.us-east.modal.run/) · [Execution](https://github.com/howdymary/mochi-demo/actions/runs/44847672231) · [Numerical audit](paperfree-v19-assessment.json) · [Choice audit](../evidence/paperfree-v19r1/choice-audit.json)

## Environment and objective

The Post-it collision geometry, visual object, forced crossing and crossing-based success requirement are removed. Drawer-to-laptop travel is ordinary flat walking. The robot still climbs the books, silences the clock, turns around, descends facing forward, closes the drawer and laptop, and rotates the globe. Book traversal remains a fixed actuator controller. No physical root repositioning, hidden support or render-only stepping is introduced.

Every measured step attempt costs one point. This includes turning, station alignment, arm-recovery steps, fixture clearance and unfinished attempts. A valid outcome receives `1000 - steps` minus bounded arm-travel and time tie-breakers whose combined maximum is 0.0011. Invalid outcomes receive -1,000,000. One fewer step outweighs all tie-breakers.

Full-route selection requires all four tasks, the unchanged balance and smoothness limits, no forbidden contact, and at least 4.5 mm median minimum-sole clearance on each flat walking leg. Shorter failed attempts cannot win. This is optimization within a finite controller library, not proof of the globally smallest step count.

The initial collection stopped before any optimizer update because a whole-route native-acceleration average was applied to truncated branch histories. The [protocol amendment](paperfree-v19r1-amendment.md) separates local branch eligibility from full-route qualification. Full-route limits, simulation, controls and evaluation scenarios stayed fixed. Prior usage, raw outcomes and superseding targets are retained.

## What Tinker trained

Tinker post-trained a Qwen3.5-4B LoRA model that selects walking, manipulation and recovery controllers from structured simulator observations. All eight updates included gradient calls for walking, clock, drawer, laptop, globe and recovery. There were 48 completed domain-gradient calls and 193,113 training-token presentations. The first update changed measured probabilities in all six domains.

Training used reward-derived supervised targets from 17 measured branch states across two training conditions, including one retained complete qualified reference. These are 17 measured targets, not 193,113 independent examples. This continuation generated no additional teaching rollouts. Checkpoints 0, 1, 4 and 8 were saved and physically evaluated on the same three development scenarios. Native ONNX gait weights and the book controller were not trained.

## Development selection

| New updates | Complete routes | Qualified routes | Steps on qualified routes |
| --- | ---: | ---: | ---: |
| 0 | 1/3 | 1/3 | 436 |
| 1 | 1/3 | 1/3 | 420 |
| 4 | 0/3 | 0/3 | Undefined |
| 8 | 0/3 | 0/3 | Undefined |

On paired scenario 212002, update 1 used 420 rather than 436 steps and 277.031 rather than 283.319 physical seconds. Recovery joint travel fell from 20.939 to 15.860 radians. Alignment steps fell from 54 to 38. Other categories together had no net reduction. This is one development pair, not a fresh-test efficiency result.

The only changed common discrete choice was the clock approach, F to H0. Walking remained W10 and recovery remained R4. Earlier actions affect later physical states. These measurements do not isolate a walking-strategy change or rule out simulator variability. The other two development cases failed during laptop contact. Later checkpoints were rejected.

Update 1 was selected before the fresh scenarios were opened. The selection record explicitly retains `held_out_opened: false`.

## Fresh tests and controls

| Policy | Complete | Qualified | Falls | Forbidden-contact attempts |
| --- | ---: | ---: | ---: | ---: |
| Parent | 1/4 | 0/4 | 0 | 3 |
| Selected update 1 | 2/4 | 2/4 | 0 | 2 |
| Fixed W8/P5/R4 control | 1/2 | 1/2 | 0 | 1 |
| Training-derived static policy | 0/2 | 0/2 | 0 | 1 |

The selected model's qualified fresh attempts, scenarios 213002 and 213003, each used 417 steps. Their mean completion time was 277.474 physical seconds. The parent finished scenario 213002 in 401 steps, but its native-acceleration RMS was 161.908 against the frozen maximum of 161.4. That attempt is retained and marked unqualified.

There are zero qualified parent/selected pairs. Paired step, time and recovery-travel reductions and their intervals are undefined. The target required four qualified selected completions, at least two qualified matched pairs, at least 10% fewer paired steps and no longer paired time. None of the missing conditions is waived.

All seven development and fresh comparisons changed only the clock choice among their common discrete decisions. Walking and recovery choices did not change. Differences in downstream steps or contact outcomes cannot be presented as evidence of a newly learned gait. The current four-case result also does not establish a reliable completion advantage over other layouts or hardware.

The fixed and static controls ran on scenarios 213000 and 213001. Their smaller cohort and different failure patterns prevent comparing successful-only mean costs as though they were matched efficiency estimates. Partial routes are diagnostic, not faster solutions.

## Services and accounting

Modal executed 21 new physical attempts: nine development evaluations, eight fresh evaluations and four controls. Including the stopped collection and previous engineering, the accounting totals 75 physical attempts and 7.991 simulation CPU-hours. Limits were 112 attempts, ten simulation CPU-hours, eight optimizer updates and four physics workers. These are execution records, not a billing invoice.

Exa performed one new failure-driven search in this continuation. Including the stopped collection, total search accounting is two. Retrieved sources informed the recorded hypothesis and design discussion. The frozen physical controller was not changed by retrieved text. No no-search comparison establishes a search benefit.

The independent [contact-location diagnostic](contact-geometry-v20.md) used five local attempts and 359.352 single-thread wall seconds under a separate eight-attempt, 1800-second cap. None of its three proposed contact changes closed the laptop from the matched failed approach. No candidate was accepted and no Tinker training occurred in that diagnostic.

### past.dev challenge

Agents: research, design, execution and review used four author identities and four explicit reader identities. The shared research audience and critic-private audience had actual access controls.

Layers: prompts held working context; past.dev held sourced hypotheses, plans, observations and conclusions; versioned code held procedures; artifact storage held exact measurements and trajectories.

Results: this continuation made six writes and six logical recalls, with five verified cross-role recalls. The designer recalled research before choosing a balanced training allocation. The critic recalled final measurements and rejected the improvement claim. The researcher recalled that verdict. A private-canary recall verified audience isolation. No ingestion remained pending. Combined with the stopped collection, accounting is eight writes and eight recalls.

Caveats: those interactions demonstrate real memory use, not a measured memory benefit. No memory ablation was performed. The private canary is a synthetic test rather than a claim of a broad security audit. API counts are not billed-credit totals.

## Replay and verification

The viewer retains twenty uninterrupted recordings: all four evaluated checkpoints on three development cases and four fresh parent/selected pairs. All attempts remain inspectable. The default fresh comparison shows the parent's quality-limit failure alongside the selected completion. The step-category table explains where measured attempts occurred without labeling every individual step unnecessary.

The separate [engineering viewer](https://howdymary--mochi-paperfree-v19-demo-web.us-east.modal.run/?mode=engineering) preserves three fixed-controller attempts. Its 468-to-414-step result preceded training and receives no Tinker credit.

The numerical audit verified all 236 frozen files, optimizer and domain-gradient counts, carried resource accounting, twenty compressed and uncompressed recording hashes, increasing physical timestamps, absence of paper crossings, no applied root force and agreement between step totals and event counts. Eight focused regression checks passed. Browser verification played the default fresh comparison continuously, inspected sixteen pair views covering all twenty unique recordings, checked task outcomes and step-category totals, and exercised the foot camera. No JavaScript exceptions or console errors occurred. [Browser verification](../evidence/paperfree-v19/browser-qa.json).

From the repository root, after the existing local environment and assets are available:

```sh
gh run download 44847672231 --repo howdymary/mochi-demo --name mochi-paperfree-v19r1-training-44847672231 --dir mochi/.cache/paperfree-v19r1-completed
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_paperfree_v19_demo.py --source mochi/.cache/paperfree-v19r1-completed --workflow-run 44847672231
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_paperfree_v19.py --source mochi/.cache/paperfree-v19r1-completed
python3 -m http.server 4120 --directory mochi/web/desk
```

Open `http://127.0.0.1:4120/paperfree-v19.html`. Public replay requires no service credentials. Exporting retained clips requires authenticated Modal access. Re-executing the trained policies also requires retained backend checkpoints and Tinker access. Large raw trajectories remain in artifact storage. The forecasting application and prior viewers are unchanged.

## Remaining work

The current bottlenecks include approach-dependent laptop contact, clearance around fixtures after contact, and a small teaching set with only one laptop target. More optimizer updates alone did not fix those problems. A subsequent study should first validate feasible approach and recovery states, collect alternatives from failed policy-generated states, then compare checkpoints against the same revised controller library. Any engineering change needs its own shared baseline. Current held-out scenarios must not be reused as a new unseen test cohort.
