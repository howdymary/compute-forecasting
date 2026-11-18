# G1 desk laboratory — visual and physical refinement

17 November 2026. [Open the interactive replay](https://howdymary--mochi-desk-tasks-web.us-east.modal.run/).

Mochi now uses a 22.1 cm miniature of the Unitree G1 model from
[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/unitree_g1).
The native CAD geometry, seven-joint arm chains, joint axes and ranges replace
the earlier procedural humanoid. A five-pose forward-kinematics test checks the
scaled arm transforms against the pinned upstream model.

This is a supported manipulation experiment. Legs, waist and three-finger
hands stay in the source stand pose; the fingers are detailed geometry, not a
new learned grasping controller. The pelvis is fixed and its support is drawn.
The two stations use separate resets. There is no walking or balance controller.
Miniature masses scale with length cubed and inertias with length to the fifth;
actuator gains, rotor inertia and contact parameters are tuned for this
simulation. This does not validate a physical miniature G1.

## What comes from Sand3D

The [Sand3D Articraft dataset](https://huggingface.co/datasets/Sandflow/sand3d-articraft)
is actually used, rather than cited as inspiration:

| Source entry | Used geometry | Modifications |
|---|---|---|
| `business_laptop` | Clamshell base, lid, bezels, trackpad, shutter | Fitted to the simulator's laptop dimensions; full keyboard and diagnostic display added |
| `classroom_globe_on_meridian` | Sphere, weighted pedestal, post, knurled knob | Fitted to the 58 mm sphere; Natural Earth print and a clear push path added |
| `desk_task_lamp` | Articulated lamp geometry | Uniformly scaled to a 420 mm human-size desk prop; static background pose |

These are reconstructed procedural assets, not photographic scans. The
physical contact envelopes remain a box for the screen and a sphere for the
globe. They match the task dimensions; the finer visual parts are not all
individual collision surfaces. The lamp is outside the manipulation workspace.

Raw USD downloads are hash checked before Blender imports them. Dataset Python
programs are not executed. The selected dataset revision, source hashes,
record-level attribution and fitting changes are retained in
`assets/realism/sand3d/downloads.json` and
`web/desk/assets/sand3d-attribution.json`. These selected records and their
Articraft sources are CC BY 4.0. G1 is BSD-3-Clause, with the full license shipped
beside the web asset. Optimized GLBs are versioned; the larger upstream USD/STL
files are fetched reproducibly and excluded from Git.

## Appearance and motion

The browser uses PBR wood maps, an HDR studio environment, graphite and satin
metal materials, softer shadows and ambient occlusion. The globe print uses
Natural Earth geography. Laptop plots show the actual untrained development
traces; they are marked as recorded. Texture and geography sources are recorded
in `web/desk/assets/sources.json`: [Poly Haven](https://polyhaven.com/license)
(CC0) and [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/)
(public domain). Powered by Poly Haven.

Every moving robot link and task object is placed from the recorded MuJoCo body
transform. The GLB display mesh uses a lighter visual LOD; native collision
meshes stay unchanged. The renderer converts glTF Y-up coordinates into native
Z-up wrappers before applying those transforms. A separate MuJoCo data instance
exports poses without altering the rollout.

`render_g1.py` also produces Cycles images from those same body poses, metre
units and fitted assets. These are rendered simulation frames, not photographs
or evidence of real-world transfer. The browser is an interactive recorded
replay, not a live simulation or a live learning session.

## Reproduce from the repository root

```sh
uv pip install --python mochi/.venv/bin/python -e 'mochi[dev]'
mochi/.venv/bin/python mochi/scripts/fetch_visual_models.py
mochi/.venv/bin/python mochi/scripts/realism_assets.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/calibrate_g1.py
mochi/.venv/bin/python mochi/scripts/build_display.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/export_g1_geometry.py
blender -b --python-exit-code 1 --python mochi/scripts/build_g1_asset.py
blender -b --python-exit-code 1 --python mochi/scripts/build_sand3d_assets.py
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest -q mochi/tests/test_g1_model.py mochi/tests/test_desk_tasks.py
python -m http.server 8773 --directory mochi/web/desk --bind 127.0.0.1
```

Blender conversion/render scripts were run with Blender 5.1.2. `build_display.py`
uses Pillow and the macOS Menlo font. It regenerates a display texture already
included in the public assets. `realism_assets.py` also requires Pillow and the
`gh` CLI to fetch pinned Natural Earth geography. Set up the venv with
`uv venv --python 3.11 mochi/.venv` first if it does not exist.

After calibration, copy the replay files for rendering:

```sh
mkdir -p mochi/artifacts/realism-v4
cp mochi/web/desk/tasks/laptop.json mochi/artifacts/realism-v4/laptop.json
cp mochi/web/desk/tasks/globe.json mochi/artifacts/realism-v4/globe.json
blender -b --python-exit-code 1 --python mochi/scripts/render_g1.py -- --task globe --frame 45 --samples 64
```

The additive deployment remains `mochi-desk-tasks`; `deploy_tasks.py` serves
only the replay, its public assets and measurements. Provider keys are not
attached to the web app. The GitHub workflow injects the existing Modal secret
references during deployment. Forecasting deployments and archived results are
unchanged.

## Evidence and next experiment

The hand-configured controller passed 8/8 laptop and 8/8 globe development
scenarios, seeds 9000–9007. Worst final errors were 1.98 and 1.38 degrees.
Displayed seed 9000 ended at 1.70 and 1.31 degrees error, with no non-hand task
object contacts. The verifier requires ±3 degrees, angular speed ≤0.07 rad/s
and 0.4 seconds of terminal settling in a seven-second episode.

All sixteen receipts are in `web/desk/tasks/calibration.json`. These checks
helped configure this environment; they are not held-out evidence, an estimate
of real-world reliability, or a before/after learning result.

No new Exa/past.dev/Tinker research campaign or Modal rollout batch has run on
this G1 environment. Modal currently hosts its static replay. Earlier puck
results and the cancelled eraser campaign are separate. The next phase must
freeze varied selection tasks and train/validation/test splits, actually
post-train the controller selector with Tinker, and compare its starting and
trained weights against a train-selected fixed controller on fresh scenarios.
