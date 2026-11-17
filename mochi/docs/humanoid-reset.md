# Humanoid and environment reset — 17 November 2026

The first direct-desk prototype had a 135 mm arm on a crouched body about
140 mm tall. Its hand reached the eraser, but the proportions did not resemble
the requested miniature humanoid. That geometry is superseded as a design.

The replacement has a standing height of 221 mm, a 34 mm head, a 56 mm torso,
40/37 mm arm segments, 52/48 mm leg segments, a 66 mm shoulder span, and
24 × 40 mm feet. The dimensional source is
`assets/robot/mini-humanoid.json`. `web/desk/rig-spec.js` is its public copy.

Open the independent geometry preview:

```sh
python -m http.server 8773 --directory mochi/web/desk --bind 127.0.0.1
# http://127.0.0.1:8773/body.html
```

The standing pose checks silhouette and scale against a full-size laptop and
coffee mug. Front, side, three-quarter and desk views are available. A separate
supported kneeling reach pose uses the same limb lengths. Both are kinematic
design views. They do not claim trained control, balance or contact validation.
There is one desktop, with no raised task platform.

Workflow 44185117343 was cancelled when the user redirected work to the robot
and environment. It completed two research rounds and began generating training
examples, but it reached no Tinker optimizer updates. Do not label that run as
post-training. The post-training implementation remains available in
`src/mochi/desk/train.py`; its old physical geometry must be replaced and tested
before it is run again. Old results must not be attached to the new robot.

Next: use the accepted dimensions in the MuJoCo model, check supported reach
and self-collision, validate the hand/eraser contact, then freeze a fresh
protocol before generating labels or post-training the selector.
