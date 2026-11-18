# Laptop clearance and support-force revision

The retained training failure, seed 23000, closed the laptop but failed validity: the falling lid briefly contacted the robot's left hip. Moving the hand target 3 mm outward did not fix it. Moving the initial stance 15–20 mm farther sideways removed that contact in isolated diagnostics.

The continuous route exposed another problem. From the farther stance, the downward press could tip the robot sideways. A route-only revision produced a timeout in one calibration and a fall in another. Those failures remain in the artifacts.

The revision therefore makes two engineering changes:

- Move the laptop stance from x = 0.300 m to 0.320 m, outside more of the lid's swept volume.
- Add a bounded X component to the existing Y-balanced arm press. The requested force points toward the foot support center, reducing the reaction moment. This changes arm actuator targets; it adds no base force.

The robot, object properties, standing controller, native gait, IK solver and success verifier remain unchanged. A conservative planning copy checks neutral standing at 17 lid angles from 0° to 80°, with a 10 mm allowance. This is sampled clearance, not continuous dynamic certification.

With the combined revision, fixed controls completed all four tasks and recoveries on known calibration seeds 19000, 19001 and 23000 without falling. These are engineering checks, not held-out or learned-policy results.

The Tinker training campaign continues unchanged. Its checkpoints 0/8/16/32/64 will be evaluated without further training on this revision. Both parent and trained weights receive the same revised setup. Development seeds 24000/24001 select the checkpoint; fresh seeds 26000–26003 are opened only afterward. The original V8 tests, 25000–25003, remain separately reported. Neither the stance change nor the force correction is attributed to weight training.

The protocol is [clearance-protocol.json](../configs/clearance-protocol.json). Execution is in [clearance.py](../src/mochi/control_v8/clearance.py), and the additional controller is [support.py](../src/mochi/control_v8/support.py). Source and revision results keep separate evidence directories. Evaluation adds zero optimizer updates and remains within the 512-rollout campaign budget.

The main demonstration remains one uninterrupted physical episode: alarm, drawer, laptop, globe, with walking and recovery between them. Separate task and shared-state recovery probes have resets and are labeled as isolated tests.
