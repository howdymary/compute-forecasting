# Arena-only target and endpoint-continuation experiment

2026-11-15 UTC. The user's explicit objective is a new Einstein Arena leaderboard record. C2's unrestricted constant is not the target: Crmarić, Kovač and Rupčić prove its supremum is 1 in https://arxiv.org/abs/2611.12685 (v1, November 9). The finite Arena input and minimum improvement rule still apply.

## Evidence motivating this batch

Original CPU polish run 43763414376 was recovered without restarting its searches, and isolated exact acceptance passed in run 43765468258. Both schedules produced byte-identical NPY witnesses (SHA256 1dce5b2b6817d04bac8003bd330804486f5c78e488a3439c2cb1e9d0acefb151). Integer quantization has exactly the ratio 2764182317012209325424310583885229346642720637 / 2868415937403266316664617946072713880495748028, approximately 0.9636616088232245. It is only about 4.68e-8 above the observed leader and does not meet Arena's 1e-5 increment. No record or submission is claimed.

The old proposer propagated the best true-score iterate, discarding endpoints with temporarily worse nonsmooth scores. This batch isolates that decision: two CPU Modal workers, same verified warm start, seed, Tinker-selected smoothing schedule and 900-second budgets. One propagates greedy best iterates; the other retains finite nonnegative optimizer endpoints. The global best remains separately checkpointed in both. Smoothing changes proposal generation, never validity or acceptance. Inner iteration limits are 80/120 evaluations with two outer steps; both arms use the same values. Equal time is the primary comparison; endpoint propagation also disables the greedy no-gain early stop because crossing that valley is the hypothesis.

The existing private Modal volume is read with create_if_missing=False and the exact warm witness certificate is reproduced before searching. No GPU request is made: the previous A100 access denial is definitive until account access changes. No billing settings are changed. The sources, dependencies and outputs remain inside codegarden/, except for the approved launcher. No workstation files or dependencies are created.

Exa supplies real method retrieval logged with query/source/adaptation. Tinker chooses one implemented schedule; it is an untrained selection, not claimed adaptation. New outputs are quantized and certified by the frozen three-prime NTT/CRT checker, cross-checked with the pinned official FFT verifier. Only a candidate clearing the live minimum margin gets a fresh isolated acceptance job. A later Arena evaluation is still necessary for a leaderboard record.

## Other bounded evidence

Hadamard block run 43766049167 checked 2550 row/column pairs and tried 284598 three-row repairs in 180 seconds without a gain. This is neither a proof of neighborhood optimality nor a global impossibility result. The strongest observed score remains 43.33745596194037. No repeated identical batch is scheduled.
