# MOCHI: Shared experiment memory and controller post-training

Methods and results using past.dev and Tinker.

[Watch the newest recording and the project’s development](https://howdymary.github.io/mochi/). Updated November 19, 2026; V15 training, evaluation and the final memory handoff are complete.

Mochi is a miniature humanoid simulated in MuJoCo. It climbs books, silences an alarm clock, closes a drawer and laptop, then turns a globe to a target. The study measures whether supervised post-training improves the model’s selection of walking, manipulation and arm-recovery controllers.

We use past.dev to carry those findings between the parts of the research workflow. Tinker updates the model that chooses walking strategies, contact profiles and arm recovery. MuJoCo supplies the physical measurements used to judge those choices.

Checkpoint comparisons hold the simulator, available controllers, scene, route and success criteria fixed. Experiment records identify the evidence used to choose the training allocation.

## Experiment records in past.dev

Rollouts record joint positions, foot contacts, body orientation and task outcomes. The research workflow uses these measurements to identify failure modes and propose changes to test.

Exact trajectories and numerical records remain in artifact storage. past.dev stores observations, hypotheses, supporting sources, experiment results and qualified conclusions. Each record includes an author, timestamp, audience and source identifier. Its record type distinguishes hypotheses from measured results.

One recorded failure involved descending before the foot had cleared a book edge. The experiment history described the falls and the subsequent development tests of staged clearance and shorter placements. That evidence became part of a shared observation, alongside findings about the clock approach and arm withdrawal. The research stage recalled it before searching for relevant methods. The design stage then recalled the sourced hypothesis before choosing a training allocation. [Memory implementation](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/desk/services.py).

In V12, the design stage selected an allocation with more recovery supervision than the balanced alternative. Training batches contained 16 recovery examples and eight walking examples per update, plus four for each manipulation task. The decision record identifies the source records used for that choice. Measuring whether memory itself improved performance would require a separate comparison without it. [Recorded findings and decisions](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/web/desk/terrain-training/report.json).

## Ingestion, source verification and access control

A successful write request does not mean a finding is ready to recall. Our integration waits for ingestion to complete before a dependent read. Pending ingestion identifiers are journaled so an interruption does not erase the state of the handoff.

On recall, we check the returned source identifiers against the record we need. Once the source is verified, we resolve its canonical payload from the experiment journal. If the required source is absent, the workflow stops that handoff rather than quietly substituting an unrelated result. This lets us use the retrieval service while retaining exact numerical and provenance records.

The workflow also separates shared findings from private review material through past.dev audiences. We tested that boundary with a synthetic private record and a read from an identity outside its audience. The completed audit recorded the expected denial. These controls matter when several processes share memory but should not share every piece of working context. [Ingestion and journaling](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/terrain_v12/services.py).

## Post-training in Tinker

Tinker trains a Qwen3.5-4B model with LoRA, which updates a smaller set of model parameters. The model reads structured observations and selects among bounded controller options. Those choices affect walking strategy, how a hand approaches and contacts an object, and how the arm withdraws afterward.

The native gait network, balance controller and manipulation primitives remain fixed during the checkpoint comparison. Tinker updates the decision model above them. Its outputs are executed through MuJoCo actuators, and the simulator measures whether the robot actually reaches the station, makes valid contact and finishes safely.

Training examples come from physical comparisons of available actions. Tinker performs gradient calculations and optimizer updates, saves checkpoints, and supplies model inference in new rollouts. [Training implementation](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/terrain_v12/train.py) and [Tinker training API](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/).

## V12 evaluation

One completed campaign performed 32 new optimizer updates. Development evaluation selected the checkpoint after the first update, rather than the final checkpoint.

On six held-out simulation scenarios, the starting model completed the full sequence in three. The selected model completed all six within the declared smoothness limits. A competent fixed controller completed five. This is a small simulation study, with no hardware validation. [Completed assessment](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/docs/terrain-v12-assessment.md).

The component checks made the result more specific. In a walking-only intervention, the starting model fell and the selected model completed the sequence after making a different walking choice. The manipulation and recovery interventions recorded the same profile choices under both models. Those checks did not establish a learned improvement in manipulation or recovery.

The final evaluation was written to past.dev, recalled for review, and followed by a qualified conclusion. The research stage recalled that conclusion before the next campaign. The stored result includes the limitations of the component tests.

## V15: Fewer steps after post-training

V15 began by recalling the earlier assessment from past.dev. A source-verified finding informed the Exa research query. The design stage read the sourced hypothesis and chose twelve walking examples and twelve recovery examples per update, with four examples for each object task. The record identifies the findings used for that allocation.

We engineered and froze turn-first navigation and bounded faster-approach options before comparing weights. Every checkpoint used the same scene, route, action library and success criteria. Modal collected 148 physical rollouts: 144 action branches from matching states and four continuous collection routes. Those experiments supplied 48 labeled observation records, reused during training.

Tinker completed sixteen new optimizer updates and 96 gradient calculations across walking, clock, drawer, laptop, globe and recovery. We retained updates 0, 1, 4, 8 and 16. The native gait network and physical controllers stayed fixed. Development evaluation selected update 16 before the final scenarios were opened.

All four policies completed all four final-test scenarios within the declared limits. The selected model averaged 476.5 footsteps and 219.5 simulated seconds, compared with 806.0 footsteps and 266.4 seconds for the parent. The paired reductions were 40.9% in steps and 17.6% in time.

The static baseline limits the interpretation. It used fixed station-specific choices derived from training labels and averaged 482.0 steps and 219.1 seconds. Its choices matched the selected model in 46 of 48 decisions. The two differences were laptop profiles. The model improved over its parent, but these results do not establish a useful adaptive-selection advantage.

Motion measures also differed. Average arm-joint travel per successful recovery increased from 5.54 to 6.93 radians, and torso roll RMS was slightly higher. Both stayed within the declared limits. The study did not demonstrate improvement in every aspect of motion.

Separate component tests compared both models from twelve identical supported states, producing 24 valid diagnostic branches. These confirmed faster flat walking and faster recovery. Recovery used more joint travel. The continuous final-test results and the isolated tests remain separate in the assessment.

The final measurements were written to past.dev, recalled for criticism, followed by a qualified conclusion and recalled again for the next research step. V15 used six memory writes and seven logical recalls, including the earlier assessment. Four identities wrote, four identities performed source-verified reads, and five within-campaign cross-role handoffs were verified. The private-canary denial test passed and no ingestions remained pending.

The campaign used 204 physical rollouts and 10.341 function CPU-hours, within its limits. The results come from four fixed-layout simulated final cases. A 4/4 completion result has an approximately 51% to 100% Wilson interval at 95% confidence. Hardware performance and a causal benefit from memory or web search remain untested.

## Unsuccessful follow-up and limitations

V13 completed sixteen updates but did not improve completion on its four final scenarios. Its final recall could not verify the required memory source, so that workflow stopped with numerical evidence preserved. V15 retained that history and used a separate experiment identity and test set.

The workflow links source-verified findings in past.dev to training decisions, Tinker checkpoints and physical evaluations. Exact artifacts preserve both the numerical outcomes and the limits of their interpretation.

[Completed V15 assessment](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/docs/efficient-v15-assessment.md) · [Frozen methods](https://github.com/howdymary/mochi-demo/blob/87ba8d482efd13c789bb200ae9424924e0f77ad1/mochi/docs/efficient-v15.md) · [Training and evaluation](https://github.com/howdymary/mochi-demo/actions/runs/44625135986).
