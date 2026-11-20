# Flat-ground foot-lift preflight

[Inspect the physical recording](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/contact-v18-preflight.html?phase=desk) · [Current training workflow](https://github.com/howdymary/mochi-demo/actions/runs/44800327838)

The fixed-controller check completed clock, book turnaround, forward-facing descent, drawer, Post-it crossing, laptop and globe in one uninterrupted MuJoCo episode. It had no fall, forbidden fixture contact or applied base force. It did not pass every smoothness criterion: lateral peak-to-peak excursion reached 6.82 cm, above the frozen 6 cm limit. It is not a qualified smooth completion.

| Measurement | Result |
| --- | --- |
| Scenario | 184002, preflight only |
| Physical duration | 331.54 seconds |
| Measured step attempts | 510, all completed |
| Moving swings with clearance measurements | 355 |
| Median moving-swing minimum sole clearance | 4.79 mm |
| Moving swings with at least 5 mm clearance | 13.24% |
| Falls and forbidden contacts | 0 |
| New optimizer updates credited to this recording | 0 |

Book traversal uses planned contact footsteps. Flat-ground travel switches to an external fixed G1 gait with much lower clearance and a fast scaled cadence. The W8 option adds a contact-gated 6 mm vertical and 2 mm forward swing reference, through bounded joint actuator commands. The opposite foot must carry load. Station alignment uses the original gait. The correction does not reposition the physical root or animate the feet.

The recorder targets 100 Hz on flat transit and 25 Hz elsewhere. The viewer uses actual timestamps and measured body transforms. The foot camera and 0.5× playback help inspect brief swings. Seeking to desk walking is an explicit inspection control; the entire continuous episode remains available from its initial state.

The earlier matched corridor diagnostic increased minimum-sole median clearance from 2.55 mm to 4.78 mm, but increased steps from 44 to 56 and time from 6.26 to 7.74 seconds. It established a clearance change, not an efficiency gain. A separate vertex-transform check on those recordings found visible-foot moving-swing clearance medians of 2.51 mm and 4.60 mm, consistent with the physical-pad trend. The display and collision soles have slightly different outlines.

This preflight used engineered controls. Tinker separately post-trains a Qwen3.5-4B LoRA model that selects walking, task and recovery controls. Native ONNX gait weights remain fixed. The checkpoint study must establish any learning benefit using matched development and fresh final scenarios. This one fixed-controller episode cannot establish that benefit or general reliability.

Execution source: `4d2be964a9be26f6697513a314a3b23a64d07b90`. Campaign: `mochi-c18-44790861532`. Corrected execution workflow: `44791618165`. The initial workflow failed during image setup, before cloud physics or optimizer updates; its service usage was carried forward.

The public recording was fetched from the Mochi-specific Modal volume and checked against the rounded export reconstructed from the full archived episode. Compressed SHA-256: `9a363cbe4df299646a8ddb90edd702ae2b82e5dd744db64ce77c3deadc613bff`. Uncompressed SHA-256: `2e71736dbf902fc59439e624ac861181c1722579d25e27070932a413891d4029`.

From the repository root:

```bash
python3 -m http.server 4120 --directory mochi/web/desk
```

Open `http://127.0.0.1:4120/contact-v18-preflight.html`. The public replay needs no provider credentials. It makes no training or service calls.
