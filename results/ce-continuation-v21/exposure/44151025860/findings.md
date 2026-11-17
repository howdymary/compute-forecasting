# What the continuation actually trained on

This audit reconstructs each completed run's exact recorded batch hash from the unchanged private input snapshot. It performs no model inference or optimization. Counts are presentations, not independent market evidence.

| Arm / ordering | Selected update | Examples to selected checkpoint | Zero-price-change labels | Small changes mapped to zero | Unique examples in full100updates | Repeated presentations in full100updates |
|---|---:|---:|---:|---:|---:|---:|
| same /17 | 20 | 320 | 280 | 0 | 942 | 658 |
| expanded /17 | 50 | 800 | 649 | 7 | 1600 | 0 |

Zero-price-change labels describe the registered nearest-level supervision. They are not forecast probabilities. Small nonzero observed movements that map to the zero class are counted separately. The same output support and quantization are preserved in both arms.

Source report SHA-256: 3faa97688d2a272b038e6aa7f1091f32060779aef030aa59dafd6366d5a4ba30
Dataset SHA-256: 2921b5ee09b24e4f18d59565a5ac7057e0673cfa31c5489de4706ce6c01dc720

Raw histories, private paths and model resources are excluded. Source permissions and attribution remain those recorded in the original data audit.

Prospective improvement is not yet established.
