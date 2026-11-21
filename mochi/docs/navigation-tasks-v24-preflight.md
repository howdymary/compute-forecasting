# Object-relative task extension

The frozen navigation campaign and this extension use separate source trees. Navigation reached its development gate before the first task-extension physical attempt: 16 of 16 qualified attempts across eight layouts, with no falls or forbidden contacts. Task engineering may run locally while the unchanged navigation campaign finishes its final comparisons. Neither the final sequence layouts nor native gait weights are opened or changed during this work.

The preflight has a twelve-attempt and one summed single-thread wall-hour ceiling, charged in addition to navigation usage under the overall 512-attempt, twelve-hour and $50 modeled-provider ceilings. Each attempt reserves at most fifteen minutes. A complete measured prefix is required before task-selector training. Static feasibility and inverse-kinematics reachability alone are insufficient.

The adapter moves hand targets with drawer, laptop hinge and globe geometry. A scratch MuJoCo state checks foot/body collisions, turning corridors and arm reach without repositioning the physical robot. All compared policies receive these same primitives. One continuous rollout must still execute the approach, real book contacts, clock interaction, forward-facing descent, drawer, laptop and globe. Existing physical task and whole-sequence verifiers remain authoritative.

The first static check after geometric corrections found feasible approaches for all three relocated flat-desk tasks in eight development layouts. Those checks assume the preceding station pose, and are explicitly not physically measured arrivals. The new outboard laptop approach and forward clearance from the book edge are controller engineering. They cannot be attributed to Tinker training.

Any subsequent task-training protocol must identify its own source freeze, measured branch states, data allocation, optimizer ceiling and unopened sequence evaluation set. Until that protocol executes, this extension has zero new Tinker updates and no demonstrated four-task generalization result.

## Initial-state repair

The first physical prefix climbed, pressed the clock, turned, descended and cleared the book edge without a fall or forbidden contact. The uninterrupted full attempt then reached the relocated drawer, but recorded no hand contact and failed. Inspection found the drawer already at zero opening: `mj_setConst` had reset generalized coordinates to `qpos0`, including the scenario's task joint states. A time-zero comparison with the original world reproduced the issue for drawer, globe, laptop and six leg joints.

The isolated task adapter now restores the original sampled full-physics/control state after the constants rebuild, once at reset. Fixtures retain their new model positions, robot mechanics and contact rules remain unchanged, and no physical state is reassigned during execution. A regression test compares every initial generalized position and velocity with the original constructor. Earlier task sources and attempts remain archived. This correction is not a training result.

Phase A is already frozen and final evaluation has begun, so its implementation is preserved. Its parent, checkpoints and conventional baselines all use the same original initial state. Its results concern that measured navigation setup, which includes a closed drawer and different fixture joint defaults. They do not validate manipulation or the repaired task initialization.
