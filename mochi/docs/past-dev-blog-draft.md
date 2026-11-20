# What a robot should remember after it falls

*Building Mochi’s learning workflow with past.dev and Tinker.*

[Watch the newest recording and the project’s development](https://howdymary.github.io/mochi/). Updated November 19, 2026; the newest campaign’s final evaluation is still running.

Mochi is a simulated miniature humanoid with a small list of chores: climb a stack of books, silence an alarm clock, close a drawer and laptop, then turn a globe to a target. The interesting work happens between attempts. A fall, a bad approach or an awkward withdrawal should change what the system investigates and how the next model is trained.

We use past.dev to carry those findings between the parts of the research workflow. Tinker updates the model that chooses walking strategies, contact profiles and arm recovery. MuJoCo supplies the physical measurements used to judge those choices.

That gives us a question we can test: does the system make better decisions after training, and can we trace the training choices back to the evidence that informed them?

## Giving an experiment a usable memory

A robot falling off a book produces plenty of data. Joint positions, foot contacts and body orientation tell us what happened. They take more work to interpret: which part of the movement failed, what explanation seems plausible, and what should the next experiment test?

We keep exact trajectories and numerical records in artifact storage. In past.dev, we store the findings someone working on the next experiment needs: the observed failure, a proposed explanation, supporting sources and the result of testing it. Each record carries an author, timestamp, audience and source identifier. Hypotheses and conclusions remain distinguishable.

One recorded failure involved descending before the foot had cleared a book edge. The experiment history described the falls and the subsequent development tests of staged clearance and shorter placements. That evidence became part of a shared observation, alongside findings about the clock approach and arm withdrawal. The research stage recalled it before searching for relevant methods. The design stage then recalled the sourced hypothesis before choosing a training allocation. [Memory implementation](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/desk/services.py).

The handoff had a concrete consequence. The design stage selected an allocation that gave arm recovery more supervision than the balanced alternative. The resulting training batches contained 16 recovery examples and eight walking examples per update, plus four for each manipulation task. The recorded decision includes the source records it used, so we can inspect what informed that choice. This establishes a real use of recalled evidence; measuring whether memory itself improved performance would require a separate comparison without it. [Recorded findings and decisions](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/web/desk/terrain-training/report.json).

## Making the handoff dependable

A successful write request does not mean a finding is ready to recall. Our integration waits for ingestion to complete before a dependent read. Pending ingestion identifiers are journaled so an interruption does not erase the state of the handoff.

On recall, we check the returned source identifiers against the record we need. Once the source is verified, we resolve its canonical payload from the experiment journal. If the required source is absent, the workflow stops that handoff rather than quietly substituting an unrelated result. This lets us use the retrieval service while retaining exact numerical and provenance records.

The workflow also separates shared findings from private review material through past.dev audiences. We tested that boundary with a synthetic private record and a read from an identity outside its audience. The completed audit recorded the expected denial. These controls matter when several processes share memory but should not share every piece of working context. [Ingestion and journaling](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/terrain_v12/services.py).

## Turning physical evidence into training

Tinker trains a Qwen3.5-4B model with LoRA, which updates a smaller set of model parameters. The model reads structured observations and selects among bounded controller options. Those choices affect walking strategy, how a hand approaches and contacts an object, and how the arm withdraws afterward.

The native gait network, balance controller and manipulation primitives remain fixed during the checkpoint comparison. Tinker updates the decision model above them. Its outputs are executed through MuJoCo actuators, and the simulator measures whether the robot actually reaches the station, makes valid contact and finishes safely.

Training examples come from physical comparisons of available actions. Completed training includes real gradient calculations and optimizer updates, followed by saved checkpoints and model inference in new rollouts. A nicer replay or a revised prompt does not count as a trained checkpoint. [Training implementation](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/src/mochi/terrain_v12/train.py) and [Tinker training API](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/).

## What the completed experiment showed

One completed campaign performed 32 new optimizer updates. Development evaluation selected the checkpoint after the first update, rather than the final checkpoint.

On six held-out simulation scenarios, the starting model completed the full sequence in three. The selected model completed all six within the declared smoothness limits. A competent fixed controller completed five. This is a small simulation study, with no hardware validation. [Completed assessment](https://github.com/howdymary/mochi-demo/blob/mochi-desk-v3/mochi/docs/terrain-v12-assessment.md).

The component checks made the result more specific. In a walking-only intervention, the starting model fell and the selected model completed the sequence after making a different walking choice. The manipulation and recovery interventions recorded the same profile choices under both models. Those checks did not establish a learned improvement in manipulation or recovery.

That distinction belongs in memory too. The final evaluation was written to past.dev, recalled for review, and followed by a qualified conclusion. The research stage recalled that conclusion. A later experiment can therefore use both the successful result and the narrower explanation of what changed.

## What the next run can inherit

The next campaign, V15, starts by recalling the earlier assessment from past.dev. A source-verified finding informs what to investigate through Exa. The design step then reads the sourced hypothesis and chooses a training allocation: twelve walking examples and twelve recovery examples per update, with four for each object task. The decision record identifies the findings it used.

Before comparing model weights, we engineered and froze a turning controller that faces the next corridor before walking forward. We also checked faster approach options in physical simulation. Every model in the new study has the same options and uses the same scene, route and success rules. This lets us ask whether training changes which options the model chooses.

Modal collected 148 physical rollouts: 144 action branches from matching states and four continuous collection routes. Those experiments supplied 48 labeled observations. Each training update reuses examples from that measured set; repeated presentations do not count as new physical evidence.

Tinker has completed sixteen new optimizer updates, each with gradient calculations for walking, clock, drawer, laptop, globe and recovery. We saved checkpoints at 0, 1, 4, 8 and 16. Update 0 is a previously trained model, not a robot starting from scratch. The native gait network and physical controllers remain fixed.

All five checkpoints completed the three development scenarios within the declared limits. The predeclared rule selected update 16, averaging 485.3 footsteps and 218.1 simulated seconds, compared with 805.3 footsteps and 265.5 seconds for the parent. Arm-joint travel during successful recovery increased, and torso roll was slightly higher; both remained within the limits. We should not turn a reduction in footsteps into a claim that every movement became smoother.

The checkpoint was frozen before opening four fresh final-test scenarios. That evaluation also includes fixed controls and static choices derived from the training data. Separate tests start both models from identical walking, manipulation and recovery states. The full final result, component attribution and final memory handoff remain pending. [Frozen methods](https://github.com/howdymary/mochi-demo/blob/87ba8d482efd13c789bb200ae9424924e0f77ad1/mochi/docs/efficient-v15.md) · [Actual training and evaluation](https://github.com/howdymary/mochi-demo/actions/runs/44625135986).

An intervening follow-up also matters. V13 completed sixteen updates but did not improve full-route completion on its four final scenarios. Our final recall could not verify the required memory source, so the workflow stopped with its numerical evidence preserved. The later project history includes that failure. It is a practical reason to keep a journal of exact artifacts and to verify a memory handoff before depending on it.

We have not isolated whether memory itself improved performance. Establishing that would require a matched experiment without shared memory. What we demonstrated was an operational chain: recalled evidence informed a training allocation, Tinker updated decision weights, and subsequent simulations measured the consequences.

For Mochi, a useful experiment produces more than a successful replay. It leaves a finding another process can retrieve, a checkpoint we can test, and a record of what the evidence supports. That is the connection we are building between past.dev and Tinker.
