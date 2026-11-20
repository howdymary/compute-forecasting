# What Tinker trains in C18

Mochi post-trains a shared Qwen3.5-4B LoRA controller selector. Its inputs are structured simulator observations and a bounded list of available actions. Its outputs choose walking strategies, contact profiles and arm recovery. The images are rendered from recorded simulation state.

Each optimizer update submits six `forward_backward` calls: walking, clock, drawer, laptop, globe and recovery. One `optim_step` follows those calls. Tinker documents that the backward calls accumulate gradients and the optimizer applies the accumulated gradients. This is the API contract used to train all six domains in one update. [Tinker overview](https://tinker-docs.thinkingmachines.ai/tinker/)

The pinned runtime uses Tinker SDK 0.39.0. The API contract was checked against the official documentation on 20 November 2026. The campaign records returned domain-loss metrics, completed optimizer calls, training-token counts, checkpoint identifiers and changes in decision probabilities.

The native ONNX gait weights remain fixed. Inverse kinematics, actuator controllers, route execution and task verifiers are also outside the trainable model. The new foot-lift correction and laptop force controls are engineered options available to every checkpoint. Training can change which option the model chooses.

Measured MuJoCo branches provide the teaching labels. Parent proposals are tested from the same saved physical state. The accepted branch then determines the main guarded trajectory, so interventions also change the later training states. Failed branches stay in the evidence. Interrupted runtime probes provide no positive labels.

The planned campaign has 16 optimizer updates and 96 domain-gradient calls. The completed counts are recorded in the campaign report. Checkpoints 0, 1, 4, 8 and 16 are saved; 0, 1, 4 and 16 receive physical development evaluations under the amended budget. New-scenario physical outcomes determine whether training helped. A changed decision probability alone does not establish better walking or manipulation.

[Training coordinator](../src/mochi/contact_v18/train.py) · [Frozen controller options](../src/mochi/contact_v18/policy.py) · [Runtime amendment](contact-v18-runtime-amendment.md) · [Current execution](https://github.com/howdymary/mochi-demo/actions/runs/44800327838)
