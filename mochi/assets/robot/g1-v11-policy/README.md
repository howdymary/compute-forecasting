---
library_name: unitree-rl
pipeline_tag: robotics
license: apache-2.0
tags:
- unitree
- unitree-g1-29dof
- mjlab
- reinforcement-learning
- onnx
- velocity
---

# unitree-g1-29dof-velocity-mjlab

Unitree **g1** policy for the `Unitree-G1-Flat` task, trained with
[mjlab](https://github.com/mujocolab/mjlab) through [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab)
(PPO, RSL-RL).

<video src="/kramp/unitree-g1-29dof-velocity-mjlab/resolve/main/replay.mp4" controls autoplay loop muted width="640"></video>

## Files

- `exported/policy.onnx`: the policy, run at 50 Hz. Its ONNX `metadata_props` carry the
  joint names, PD gains, default pose and observation layout.
- `params/deploy.yaml`: the configuration Unitree's C++ controller loads next to the policy (generated from the ONNX metadata and `params/env.yaml` by `push_to_hub.py`).
- `params/env.yaml`, `params/agent.yaml`: the full training environment and PPO settings.
- `config.json`: the robot folder, training framework, task and source revision.

## Inputs and outputs

- **Input** `obs`: 98 floats, in this order:
  1. `base_ang_vel`: 3 values
  2. `projected_gravity`: 3 values
  3. `velocity_commands`: 3 values
  4. `gait_phase`: 2 values
  5. `joint_pos_rel`: 29 values
  6. `joint_vel_rel`: 29 values
  7. `last_action`: 29 values
- **Output** `actions`: 29 joint position actions. Each target is
  `offset + scale * action`, with `offset` and `scale` per joint in `params/deploy.yaml`.

## Deploy

Test in simulation ([unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco)) before the real robot.

```bash
git clone https://github.com/unitreerobotics/unitree_rl_mjlab
cd unitree_rl_mjlab/deploy/robots/g1
# the Velocity state runs the last policy folder in config/policy/velocity
hf download kramp/unitree-g1-29dof-velocity-mjlab --local-dir config/policy/velocity/v1
mkdir -p build && cd build && cmake .. && make   # requires unitree_sdk2
./g1_ctrl --network=lo   # start unitree_mujoco first; on the robot: --network <ethernet interface>
```

## Sim2sim check (MuJoCo)

The files in this repo were downloaded and run in MuJoCo with Unitree's sim2sim model
([unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco) `g1/scene_29dof.xml`, 2 ms physics step) by
`scripts/sim2sim_hub.py`, which reproduces the deploy controller's observation and PD semantics, at a constant
0.5 m/s forward command: the robot stayed up for the full 20 s, at a mean forward speed of 0.41 m/s.

<video src="/kramp/unitree-g1-29dof-velocity-mjlab/resolve/main/media/sim2sim_mujoco.mp4" controls autoplay loop muted width="640"></video>
