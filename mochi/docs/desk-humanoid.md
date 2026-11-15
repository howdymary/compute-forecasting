# Mochi desk humanoid, design 02

The new visual direction is an original 22 cm engineering humanoid standing on a human-sized desk. It replaces mascot proportions with a compact helmet, optical visor, split chest panels, exposed actuator housings, finger grippers, segmented limbs, and broad rubber-soled feet. Warm white, graphite, and brushed alloy dominate; safety orange is a small identification accent.

The Blender script is `mochi/assets/blender/desk_humanoid.py`. All robot and prop geometry is procedural and original. Named pivots form a design rig; they are not evidence of an actuated physics model. The laptop, 95 mm mug, 18 cm pencil, and mouse establish scale. The static scene deliberately has no animated success or fabricated task metric.

Render from the repository root:

```sh
blender --background -t 4 --python mochi/assets/blender/desk_humanoid.py -- --out mochi/artifacts/design-v2
blender --background -t 4 --python mochi/assets/blender/desk_humanoid.py -- --out mochi/artifacts/design-v2-character --view character
```

## Proposed task: the unauthorized lunch break

Mochi rolls a marble down a taped lane to knock over pencil-cap skittles while avoiding a full-size coffee mug. It is amusing because the robot treats this tiny game as a serious research problem. Useful stages are reliable release, single-pin contact, three-pin interaction, then an obstacle. Each stage needs a MuJoCo model, immutable success verifier, and paired evaluation before being presented as implemented.

For an MVP, support the pelvis or rigidly anchor the feet and describe the task as supported manipulation. Unsupported standing, walking, and a functioning dexterous hand are separate controller projects. Do not imply that adding Blender pivots supplies those capabilities.

## Separate expanded service study

`mochi/src/mochi/robustness.py` uses the existing supported pushing simulator. Its eight-round study addresses V1's poor changed-condition performance with a balanced friction/mass development mixture, fresh held-out seeds, and a conventional search with access to the same four controller families. The registered maximum is 2,016 simulations. Exa informs each research round, four roles exchange source-verified records through past.dev, Tinker chooses bounded actions, and Modal runs the physical rollouts. The new visual rig is not evaluated by this study.

Results remain separate from the original 188-rollout experiment. Extra service use is not itself evidence that research or memory improves performance. A causal claim would require matched no-search and no-memory ablations.
