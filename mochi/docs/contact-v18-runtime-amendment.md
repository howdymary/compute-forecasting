# C18 runtime amendment before training

The first three parent development evaluations completed before any optimizer update. Two finished the four-task route, one met every quality limit, and none met the moving-foot-clearance target. All three closed the laptop. The measured input durations included 1425.90 seconds for one completed route, making a 2400-second limit too short for two sequential evaluations in one worker.

The campaign therefore extends only the paired runtime envelope to 3600 seconds. The original evaluator is called unchanged inside that worker. Physics, controllers, observations, actions, success checks, quality limits, training and final scenario seeds, optimizer updates and learning rate stay fixed. All 210 support files other than the training coordinator retain their prior hashes.

To retain the 160-attempt and 14-CPU-hour bounds:

- Save and probe checkpoints 0, 1, 4, 8 and 16.
- Physically evaluate checkpoints 0, 1, 4 and 16 on the same three development scenarios. Update 8 remains saved but is not physically evaluated or eligible for selection.
- Keep all four fresh parent-versus-selected pairs, with unchanged improvement criteria.
- Evaluate fixed and static controls on the predeclared first two final seeds, 186000 and 186001. Compare those controls only with the selected outcomes on the same seeds.

These choices were frozen before training and before any final-test scenario was opened. They reduce secondary evaluation breadth rather than changing the criteria after seeing final results. The smaller control cohort must be reported as two scenarios.

Execution 44791618165 was cancelled with zero completed optimizer updates. Its four completed cloud rollouts, parent state, research records and API usage are retained. Two teacher inputs were terminated during their first candidate ascent. Each logged only attempt 2, and no candidate or teacher archive was created. Four unfinished physical stages and a conservative eight CPU-minutes are charged. The unused reservations are reconciled, not reset. All 65,927 accounted inference tokens are retained, including the two unfinished input caps.

[Exact reservation reconciliation](../evidence/contact-v18/runtime-reconciliation.json) records the before and after counters and provider input IDs. A short cloud diagnostic reaches the original action validator through the wrapper, using an intentionally invalid action after physical initialization. That failed attempt is charged and supplies no training label. The maximum planned total after this amendment is 158 physical attempts, including this probe and the interrupted-stage bound. Every runtime reservation remains subject to the original 160-attempt, 14-hour and 16-update limits.
