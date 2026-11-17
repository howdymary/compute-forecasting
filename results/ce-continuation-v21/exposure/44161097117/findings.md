# What the continuation actually trained on

This audit reconstructs each completed run's exact recorded batch hash from the unchanged private input snapshot. It performs no model inference or optimization. Counts are presentations, not independent market evidence.

| Arm / ordering | Selected update | Examples to selected checkpoint | Zero-price-change labels | Small changes mapped to zero | Unique examples in full100updates | Repeated presentations in full100updates |
|---|---:|---:|---:|---:|---:|---:|
| same /17 | 20 | 320 | 280 | 0 | 942 | 658 |
| same /29 | 50 | 800 | 686 | 1 | 942 | 658 |
| same /43 | 50 | 800 | 676 | 0 | 942 | 658 |
| expanded /17 | 50 | 800 | 649 | 7 | 1600 | 0 |
| expanded /29 | 20 | 320 | 243 | 1 | 1600 | 0 |
| expanded /43 | 50 | 800 | 628 | 5 | 1600 | 0 |

Zero-price-change labels describe the registered nearest-level supervision. They are not forecast probabilities. Small nonzero observed movements that map to the zero class are counted separately. The same output support and quantization are preserved in both arms.

Source report SHA-256: 7e5a1f9bb18f89162285a1a4fc1b69ee9bf0ab001544117bdab330982b9659ce
Dataset SHA-256: 2921b5ee09b24e4f18d59565a5ac7057e0673cfa31c5489de4706ce6c01dc720

Raw histories, private paths and model resources are excluded. Source permissions and attribution remain those recorded in the original data audit.

Prospective improvement is not yet established.
