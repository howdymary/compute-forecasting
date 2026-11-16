# Direct-model sampling correction

The v12 study genuinely optimized forecasting weights. Its forecast-distribution evaluation used a fixed request seed with `num_samples=64`. A [bounded diagnostic](../results/direct-v12/diagnostics/43961668575/sampling.json) found identical vectors within fixed-seed requests, while unset-seed and distinct-seed requests varied on the same development prompts. This also occurred on a nonmarket control prompt. We therefore treat the zero-width intervals as a sampling implementation failure, not proof that model uncertainty is intrinsically zero.

The [registered v13 control](../configs/direct-sampling-v13.json) reuses the original development-selected weights, changes only sampling-seed handling, retains all 64 realized samples per task, and compares against the same unadapted model and exact native references. It does not retrain or reselect the checkpoints. Original v12 results remain available and unchanged.

All dates remain retrospective. Corrected sampling may improve or worsen loss; it does not establish future accuracy or a news benefit. Exact numerical reproduction uses saved samples; stochastic regeneration need not be byte-identical.

ALFRED vintage downloads also timed out through both GitHub-hosted and Modal egress. No BLS features have entered these model weights. Original BLS detailed-report archives are being assessed as a separately identified alternative; current revised data cannot replace historical vintages.
