# Tinker policy review

Four real Qwen3.5-397B-A17B decisions were executed in
[run 43671753698](https://github.com/howdymary/compute-forecasting/actions/runs/43671753698).
They produced four certified structural insertions. The uncached-rate token estimate was $0.0182151.

The deterministic numerical ranking in
[run 43671271112](https://github.com/howdymary/compute-forecasting/actions/runs/43671271112)
and the model policy started from the same exact witness from run 43670827227.
Each had four structural insertion attempts, the same bounded proposal set generator and Newton solver.
This matches experiment counts, not wall-clock time or total dollars.

The deterministic branch returned the stronger certificate:

- Numerical ranking: 1.6748942113071162287645651731628015389078200425658263583947935815…
- Model selection: 1.6748942113071162287645651731627927943089243902190589963601916305…

The difference is about 8.74 × 10⁻³³. Both improve the starting witness.
This tiny comparison on one adaptive trajectory does not establish a general policy-performance result.

## A useful failure

Some recorded model explanations incorrectly treated an absent projected value as a missing observation,
and referred to failed trials when the supplied history marked successful insertions.
These explanations are not mathematical evidence and must not be presented as correct deductions.

In this problem, an insertion may create a previously zero-mass value of X, Y, X+Y or X+2Y.
That creates an entropy cost in a competing projection. It is not a data-quality problem.
The numerical heuristic accounts for this through the positive insertion exponent
1 − sum of the dual multipliers for newly created projected values.

The subsequent prompt explicitly defines that meaning, names all four projections and explains
accepted=true. This prompt correction has not been used to claim improved model performance.
No fine-tuning was performed; four decisions are not a useful independent training/evaluation corpus.

The exact verifiers determine acceptance. Language-model explanations never override them.
