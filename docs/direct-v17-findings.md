# Frozen tail-readout diagnostic

Post-hoc retrospective comparison; no training or inference was performed.

Both base and selected SFT receive the same nine-candidate development-only calibration selection.

| Model | Seven-day loss | Coverage | Width |
|---|---:|---:|---:|
| base_original | 0.0409712518 | 37.88% | 0.069402 |
| base_calibrated | 0.0403566800 | 42.42% | 0.096617 |
| sft_original | 0.0462887607 | 40.91% | 0.099975 |
| sft_calibrated | 0.0451849457 | 51.52% | 0.201190 |

Original SFT-minus-base gap: +0.0053175089.
Calibrated SFT-minus-base gap: +0.0048282658.
Prespecified descriptive repair criterion met: False.

These results cannot establish prospective improvement or repair the original training claim. Original frozen outputs and future protocols remain unchanged.
