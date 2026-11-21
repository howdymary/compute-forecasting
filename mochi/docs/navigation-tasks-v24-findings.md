# Object-relative task preflight

The extension did not validate a complete four-task route. It used its declared twelve counted physical attempts and approximately 0.35 conservatively accounted single-thread wall-hours. It made no Tinker optimizer updates. The original eight-layout final sequence set remains unopened. The separate navigation study and earlier complete demo are preserved.

| Measured attempt | Outcome |
| --- | --- |
| Initial book prefix | Climbed, pressed the clock, turned around, descended facing forward and cleared the edge without a fall or forbidden contact. |
| Initial complete-route attempt | Reached the drawer but failed. Scene-constant rebuilding had reset its sampled opening to zero. |
| Repaired initialization | Closed the drawer; a hand then clipped the printer on a minimum-margin transit. |
| Wider staging | Avoided that collision and reached the laptop. Its lid stalled against the stapler. |
| Task-workspace correction | Moved the stapler to the notebook at reset. Clock, drawer and laptop completed; a wrist hit the globe during the transition. |
| Southwest globe approach | Still contacted the globe. This isolated branch retained an error summary but no trajectory. |
| Recovered-arm holding | Retained the arm targets through position actuators during navigation. The measured component still contacted the globe and was rejected. |

All complete prefixes use one uninterrupted physical rollout. Component probes restore SHA-verified states from those recorded training prefixes and are labelled as branches. They are never spliced into a complete demo. The count includes three short snapshot-check attempts, two laptop-release branches and two globe-transition branches, as well as five physical prefixes. Earlier sources, failures and checkpoints are retained.

The strongest diagnosis is that navigation feasibility must include both the robot's changing whole-body envelope and each articulated object's operational volume. A route to the laptop is insufficient if a stapler prevents its lid closing. A static recovered-arm pose is insufficient if resuming the native gait changes the arm motion near the globe. Holding the arms alone did not resolve the measured transition, so that explanation is not treated as a proven complete fix.

The added workspace check reproduces the original laptop/stapler interference using scratch MuJoCo data without changing the physical simulator state. The corrected arrangement passes that geometric check and physically closes the laptop in the later continuous attempt. Static checks still do not establish dynamic success. Book-height generalization, a successful globe departure and complete-sequence reliability remain unestablished.

Task-label collection is disabled until a qualified complete prefix is validated. Spending on task training without a viable measured action at the failed transition would not establish improved task control. The next engineering test should retreat into clear turning space before changing heading, verify the full dynamic body envelope, and then rerun the complete route. Any new comparison needs its own source freeze and a task-feasible final cohort selected without policy-performance filtering.

[Numerical preflight evidence](../evidence/navigation-tasks-v24/preflight.json) · [Initialization and protocol details](navigation-tasks-v24-preflight.md). Full local recordings are in `artifacts/navigation-tasks-v24/`; the one summary-only branch and the failed snapshot setup are explicitly identified in the evidence.

## Separate departure probe

After closing the twelve-attempt preflight, a separate probe allowed at most six component attempts and thirty wall-minutes within the original study resource ceilings. Three attempts were executed, consuming 0.0174 single-thread wall-hours. The first stepped backward before turning but contacted the globe during its approach. Reducing the retreat crouch caused a fall in the second attempt and was rejected. The third restored the deeper crouch, preserved the direction of bounded alignment commands, and settled before handoff. It avoided falls and forbidden contacts, then stopped because no clear reachable globe pose passed the geometric and IK checks.

These are controller-engineering branches from a recorded training state. They do not complete the four-task sequence, train a neural model, or establish generalization. Three unused attempt slots were left unspent because the physical task prerequisite remained unmet. The original twelve-attempt record and all three additional failures remain archived. [Departure evidence](../evidence/navigation-tasks-v24/departure-r2.json).
