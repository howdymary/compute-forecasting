# Visual and motion experiment V22

This experiment preserves the existing Inkling demo and its physical results. It adds a separate visual comparison and an isolated GMR/mink motion prototype. Appearance changes and physical controller changes are evaluated separately.

The reference is the paper-free desk with the accepted C21 clearance waypoint, H0/C/P5/G0 task choices, W10 walking and R4 recovery. The previous 239-file physical freeze remains unchanged. Original web assets and rendering modules are also hashed before work begins. New assets, code, data and deployment names use V22 paths.

## Visual work

Improve robot and prop materials, lighting, contact presentation and asset delivery. Keep task-relevant dimensions, body bindings and joint pivots aligned with the authoritative simulation. Use identical trajectory timestamps and camera conditions for appearance comparisons. Mesh optimization must preserve body names, extras and transforms. Compression benefits are measured rather than assumed.

## Motion work

Pin GMR to commit `25f56db79ac411258b377b6d4ccba0c8ff3372ac`. Install mink 1.4.0 and MuJoCo 3.10.0 in an isolated reference-generation environment. The existing physical executor remains on MuJoCo 3.3.7. Generated configurations are references only; the physical robot moves through actuators and contact. No floating-base pose assignment or render-space foot locking is permitted.

First verify real GMR retargeting and mink solves, with input/output hashes, dependency versions and call counts. Identify the reference-data source and its license. Distinguish synthetic references, measured robot trajectories and human motion capture.

Test walking, turning and arm recovery from matched saved development states before attempting full sequences. Freeze candidate definitions and use the existing validity constraints. A shorter failed attempt is not an efficiency improvement. Keep rejected candidates and error receipts.

Limits: 32 physical attempts, four summed single-thread simulation wall-hours, at most four physics workers. Component attempts reserve up to 300 seconds and full attempts up to 900 seconds. Reference generation and rendering are reported separately. There are zero planned Tinker optimizer updates in this library-integration pilot.

Select candidates on development data only. Final from-reset comparisons use seeds 226000 through 226003, unopened until selection is frozen. Complete all four tasks, preserve safety and support limits, and compare steps, time, foot sliding, sway, native joint acceleration and recovery/intertask arm travel. Report sample counts, failures and uncertainty. If no candidate improves physical motion, retain the reference and show the negative tests.

## Delivery

Publish a separate demo with appearance and motion modes. The appearance mode replays identical physical data through the original and revised rendering. Motion mode identifies the exact controller and scenario on each side, and shows real simulated outcomes. The existing C21 deployment is not replaced.
