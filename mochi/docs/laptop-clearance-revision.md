# Laptop swept-volume clearance revision

The retained training failure23000 closed the laptop but failed validity: the falling lid briefly contacted the robot's left hip. Moving the hand's target3mm outward did not fix it. Separate initial-state interventions15mm and20mm farther sideways both closed the lid without non-hand contact or a fall. Those are engineering diagnostics on known training data, not held-out results or learned-policy gains.

The revised route moves the laptop stance from x0.300to0.320m, with corresponding approach/departure segments. The robot, object properties, controller code and success verifier are unchanged. A conservative planning copy checks neutral standing against17 lid angles from0to80degrees at5degree increments, with a10mm allowance. This is sampled clearance, not continuous dynamic certification. Full uninterrupted rollouts must still verify it.

The current Tinker training run continues unchanged. Its checkpoints0/8/16/32/64 will be evaluated without further training on the revised stance. Both parent and trained weights receive the same revised setup. Development24000/24001 selects the checkpoint; fresh26000–26003 scenarios are opened only afterward. The original V8 tests25000–25003 remain separately reported. Neither changes to the route nor physical closure are attributed to weight training.

The protocol was declared before the new tests: [clearance-protocol.json](../configs/clearance-protocol.json). The execution module is [clearance.py](../src/mochi/control_v8/clearance.py). The original training source and results remain in their own artifacts and evidence directory. Additional evaluation performs zero optimizer updates and remains inside the512-completed-rollout campaign budget.

This revision also runs separate task and shared-state recovery probes. The main demonstration stays a single physical episode: alarm, drawer, laptop, globe, with walking and recovery between them. Isolated probes have resets and are labeled separately.
