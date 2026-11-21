# Final-heading alignment repair

The first physical training probe completed one real Tinker optimizer update. On its second training layout, direct, buffered and careful routes all reached the last approach and timed out. The direct recording contains 345 switches between travel heading and final-task heading. At 28 mm from the goal, gait sway repeatedly crossed the same threshold that selected those opposing commands.

The run stopped without inventing a successful training label. Its checkpoint, actual update receipt, failed candidates and usage remain in `mochi-nav23-20261121b`. No final layout was opened.

The isolated `navigation_v23/navigation.py` repair latches the final-heading phase until distance exceeds a separate 56 mm exit threshold. Local position correction remains bounded, including backward correction while aligning. The robot still moves through the fixed native gait and actuators. The archived navigation module is unchanged.

Review also found that the old supported-hold implementation stopped checking position during its dwell. Some reported intermediate arrivals had drifted slightly beyond the declared 12 mm tolerance. The new implementation enforces that same tolerance throughout dwell and resumes physical control if capture drifts out. This strengthens implementation of the existing criterion; the tolerance is not relaxed.

Both matched failed-route profiles then qualified on the same layout and physics seed. Direct used 334 steps in 46.19 physical seconds; buffered used 392 steps in 51.82 seconds. They had previously timed out after 569 and 601 attempts respectively. A previously qualified engineering layout still qualified, using 144 steps in 19.56 seconds. These three probes are controller-engineering evidence, not learned-policy improvement.

Every parent, trained checkpoint and conventional baseline is rerun under the repaired implementation in `mochi-nav23-20261121c`. Final splits remain unopened and unchanged. The exact saved untrained parent is restored; the interrupted trained update is not promoted. Its usage remains charged, leaving at most fifteen further updates under the original sixteen-update total ceiling. Checkpoints are parent, 4, 8 and 15, with an actual-endpoint fallback if the bounded training layouts do not provide enough valid labels.

All failed training layouts stay in the records. A candidate set with no qualified action supplies no supervised label and consumes no optimizer update. It is not removed from development or final evaluation. Such cases remain evidence that the action set or controller is insufficient.

The retry-memory implementation also now creates distinct identities for each case audience. A study-level reader must fail to retrieve the case-local failure record before its authorized case reader can use it. Final outcomes cannot enter another layout's first attempt.

The original private and shared memory records, frozen source versions, untrained checkpoints and earlier demonstrations are preserved. Resource accounting carries the two interrupted campaign attempts, all actual physics and conservative unused reservations. No checkpoint was deleted and no billing setting changed.
