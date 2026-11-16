# A continuous chart of learned experiment selection

The 30-second learning-curve film keeps one chart on screen throughout. It compares development quantile pinball loss against actual optimizer updates for all six SFT runs. It does not plot price levels, final-evaluation scores, or RL runs.

## Visual choice

Three treatments were considered:

| Treatment | Readability | Motion | Decision |
| --- | --- | --- | --- |
| Six independent colors | Several identical paths hide one another; a six-item legend adds decoding | Easy to reveal, but overlap is confusing | Rejected |
| Shared exact paths, four trajectory groups, direct labels | Every run is named; identical hard-target paths are explicitly grouped | One synchronized reveal with calm checkpoint pauses | Selected |
| Grayscale field with one spotlight at a time | Good detail for one run, weaker simultaneous comparison | Smooth, but requires more attention shifts | Rejected |

The three hard-target seeds share exactly one path. Cobalt emphasizes soft/17, emerald soft/29, amber dashes soft/43, and muted ink the hard-target group. Coincident partial segments retain the same coordinates. End labels stack with leader lines; data points are never jittered.

Every dot is a measured checkpoint. Straight joins are visual guides, not additional evaluations. Open rings mark the original development-selected checkpoint, including earlier-update tie handling. The paper background and handwritten observations are supporting details rather than a dashboard.

## Evidence and scope

The source registry is [campaign-v2-checkpoints.json](campaign-v2-checkpoints.json). Every one of the 24 source points is checked against hash-verified archived development reports and reconstructed from their cell losses. Selected updates and exact full-trajectory grouping are verified independently.

Development comprises six tasks, 18 series-horizon cells and three dependent dates: August 8, 15 and 22, 2026. Training seeds do not create additional independent market observations. All six runs meet at update 50's development loss; five share update 100's loss. Equal loss does not establish equal predictions.

The one supporting percentage is the operational soft/17 development change from 0.01482266973639115 to 0.009050336633428241: 38.94260079742078% lower. It is rounded to 38.9% in the film. The separate 22.8% retrospective evaluation result is not plotted. Neither prospective accuracy nor incremental RL improvement is established by this visualization.

The original price-forecast replay remains archived under its own run IDs and is not overwritten.

## Reproduce on a remote runner

Run the **Render continuous Tinker learning curve** GitHub Actions workflow on compute-observatory. It installs pinned Playwright 1.65.2, Pillow 13.0.0 and Modal 1.6.4 on the hosted runner. No Tinker request, model sampling, forecast fit or numerical experiment is launched.

The rendering command is:

~~~sh
python -m compute_forecast.record_learning_curve
~~~

Public readers can render without any provider credentials on a remote runner using:

~~~sh
python -m pip install -e . playwright==1.65.2 pillow==13.0.0
python -m playwright install --with-deps chromium
# Install ffmpeg using the runner's package manager.
python -m compute_forecast.record_learning_curve --no-publish
~~~

Inputs are permitted committed documents and the immutable public research archive. The existing public notebook font is embedded in the HTML to avoid network-dependent font rendering; its OFL license is retained. Private model resources and raw GPU offers are unnecessary.

## Validation and publication

Chromium renders exactly 900 frames at t = frame / 30. PNG buffers stream directly to FFmpeg, producing a 30-second 1920×1080 H.264 MP4 with fast-start. Animation timing is independent of runner speed. SVG geometry and font loading are validated before encoding.

Checks cover 24 source checkpoints, six original selections, exact grouping, fixed axes, immutable dot geometry, monotonically advancing reveal position, text clipping and direct-label collisions. The output is checked for 900 frames, 30 fps, resolution, duration, codec, public-byte hash and HTTP range support.

Full-resolution source stages and extracted encoded frames are retained. The contact sheet covers all major stages; the motion strip samples the actual encoded line reveal every 0.3 seconds. They support visual inspection of clipping, legibility, shared paths and smooth progression.

Versioned publication: results/terminal-v10/runs/<workflow-run>/learning-curve/.

That folder contains chart-data.json, validation.json, manifest.json, publication.json, replay.html, caption.txt, OFL.txt, poster.png, contact-sheet.png and motion-strip.png. The self-contained HTML includes play/pause and a time scrubber for reviewing the same composition; those controls are hidden in the film. MP4 bytes use the existing public media route without redeploying the application.

Implementation references: [Playwright screenshots](https://playwright.dev/python/docs/screenshots) and [FFmpeg image2pipe](https://ffmpeg.org/ffmpeg-formats.html#image2pipe).
