# Training plan and completed assessment

Final outcome: 96 updates and 480 domain-gradient calls completed. Fresh Modal tests reached 20/20 waypoints versus 0/20, and one of four full routes versus zero. Isolated laptop closing improved from 0/4 to 2/4; alarm success regressed from 4/4 to 3/4. The fixed classical controller also completed one of four routes. [Full results](refinement-v7-results.md).

The following plan was recorded while the run was active. The pre-existing V7 run (Actions 44255635428, source b459cadaaa34dfbecfaef5fa841a7298475fced0) was already active when this request arrived. It trains Qwen3.5-4B LoRA command/profile decisions with five domain-gradient calls per optimizer update. The fixed cap is 96 updates; it stops at 64 only if both development routes pass. No duplicate study is launched.

## Learned and fixed components

Tinker learns repeated body-velocity commands and alarm, drawer, laptop and globe contact-profile choices. The native Unitree gait weights, high-frequency phase, balance servos, arm IK, world and success rules are fixed. This is locomotion-command and contact-profile post-training, not training foot placement or motor torques from scratch.

The V7 model starts from the archived update-zero state of V6. Its updates are a separate study; they are not cumulative continuation from V6 update 64. Starting and trained policies use identical geometry encoding and controllers.

## Evidence so far

The completed V6 Modal replication reached 8/8 isolated navigation goals after training versus 0/8 before. Its full-route test remained 0/4 versus 0/4; the fixed classical controller completed 2/4. This negative route result motivated V7. The earlier Linux reference achieved 1/4 routes; its successful presentation example is not a reliability estimate.

## Movement assessment

`motion_metrics.py` measures matched initial windows (up to 20 seconds, shortened to the earliest episode end for each seed) from actual 25 Hz trajectories: torso tilt, walking path, yaw travel, turn reversals and requested command changes. These diagnostics were added after V7 started. They are explicitly post-hoc, not a retroactively claimed training reward. Recorded loaded-foot slip spans the whole episode and must not be presented as walking-only slip. Motor work, true sole clearance and high-frequency jerk are unavailable in these historical recordings.

Side and foot inspection cameras use fixed world-relative offsets and the same playback speed. They change no physical trajectory. No cosmetic foot locking or root animation is added.

## Research memory

The frozen V7 implementation exchanges observations, sourced hypotheses and proposals through past.dev at initialization and update 16, and writes a final criticism. Verified recalled proposals choose 48 walking + 4 examples per task or 32 walking + 8 per task, always training all five domains. This cadence is not a memory interaction at every optimizer update or every checkpoint. The UI exposes verified source handoffs and measured call counts. Credit charges are not inferred from call counts.

## Budget and selection

The active run retains its 96-update cap and 100-minute workflow cap. Existing checkpoints and other work are preserved. Development seeds 15000/15001 control the frozen stopping rule; final route seeds 16000–16003 and isolated navigation seeds 16500–16507 remain sealed until selection. The primary checkpoint recording uses the first declared development seed, 15000. Every test outcome is exposed.

A separate motor-level gait-learning claim requires an implemented and evaluated training mechanism; this study does not establish it. If the frozen budget produces no physical gain, the negative result is retained.
