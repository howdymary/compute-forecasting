# Tinker checkpoint forecast replay

A requested 30-second, 1920×1080 silent recording of actual saved checkpoint results. The cream notebook scene is a dedicated evidence replay, rather than a live inference session.

The illustrative case was selected retrospectively after inspecting all six development tasks, to show actual price-forecast changes. It is not a registered performance endpoint. The first 20 seconds hold one A100 SXM 80GB series and the August 15, 2026 development origin fixed while replaying operational soft-target seed 17 checkpoints 0, 20, 50 and 100. Historical prices come from the matching approved public history adapter. Quantile forecasts and compatible archived outcomes are read from existing retained numerical outputs; no numerical fitting or training is launched. Dashed joins guide the eye between actual 1-, 3- and 7-day points.

The sidebar reports aggregate development loss, whose scope differs from the single-case price chart. The update-20 regression is retained. The next five seconds show all six SFT runs; the three hard-target trajectories overlap exactly. Rings identify the original development-selected checkpoints.

The last five seconds report the separate retrospective comparison: operational SFT loss 0.011569797542840439 versus starting-policy loss 0.014995328587716763, on 12 matched cells across two A100 series and three reused, dependent dates. A100 40GB worsened; the pooled gain is concentrated in SXM 80GB. The three selected RL checkpoints remained their update-zero SFT parents. This does not establish prospective accuracy, H100 policy performance, or an accuracy improvement at every checkpoint.

## Reproduce remotely

Run **Record requested Tinker training progression** on compute-observatory. It requires the existing Modal credentials and retained numerical files. It does not request Tinker sampling or training.

The workflow verifies the immutable research ZIP and member hashes, every development checkpoint score, series publication approval, quantile ordering, exact case identity, and recomputed pinball agreement with the saved cells. It records Chromium, encodes H.264 with fast-start, verifies duration/resolution/frame rate, and checks the public MP4 hash and HTTP range support.

Versioned artifacts appear in results/terminal-v10/runs/<workflow-run>/training-video/. The manifest and replay data retain sources, hashes and scope. Video bytes use the existing public media route, keeping source changes outside the deployed application.

The current official CSV, study configurations, checkpoints, and numerical results remain unchanged. Historical attribution and component licensing are retained in the replay data and the project's [data source index](DATA_SOURCES.md).

Sources: [measured findings](campaign-v2-findings.md), [checkpoint registry](campaign-v2-checkpoints.json), [mechanism audit](review-v4-findings.md). Implementation references: [Playwright videos](https://playwright.dev/python/docs/videos), [Modal Volumes](https://modal.com/docs/guide/volumes).
