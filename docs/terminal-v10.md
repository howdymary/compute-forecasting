# GPU pricing terminal v10

The [full-screen terminal](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/advanced) follows the supplied dark financial-chart reference: a source-separated GPU watchlist, dominant precise price chart, derived lower panels and a right-side variable panel. The original Explore/Research views remain available from Overview.

The terminal reads only the existing verified pricing and approved history APIs. Actual submitted q10/q50/q90 values, the November 6 cutoff, missing historical days, units and exact target identity are preserved. Daily price changes require consecutive observations; there is no volume or OHLC fabrication. The optional EMA 20 is descriptive, resets at gaps and requires 20 consecutive observations. It does not change forecasts.

Rental and hardware-resale scenarios remain distinct assumption calculations. Index 100 is the default. Rental-dollar mode uses the explicitly dated last approved matching historical rate, and is disabled without that anchor. Monthly compute spending is the calculated rate multiplied by user-selected GPU-hours; it is not realized revenue. Rates compound monthly as start * (1 + annual change)^(month/12), or index 100 * (1 - depreciation)^(month/12) for resale.

Source and saved-point drawers retain exact identities, original values, input assumptions, artifact links and the official CSV checksum. No new training or accuracy claim is introduced.

## Recording

A separate requested recording workflow captures an actual 60-second browser exploration and encodes 30 seconds at 2× speed, 1920×1080, H.264. It uses only frozen public API responses, with their hashes retained, and labels the capture as recorded exploration. The tour covers all submitted series and then changes the right-side scenario assumptions. Parameter changes generate explicit calculations; they do not alter archived forecasts.

Recording is initiated only by a committed request configuration or manual dispatch. Existing video files and recording workflows remain unchanged. The new MP4 is versioned separately, with a source-state trace, ffprobe duration, frame checks and hashes. It is published only after numerical and visual checks.

Implementation references: [Playwright Python video recording](https://playwright.dev/python/docs/videos), [FFmpeg setpts](https://ffmpeg.org/ffmpeg-filters.html#setpts_002c-asetpts), [Modal Volume upload and reload](https://modal.com/docs/guide/volumes).

## Verified delivery — 15 November 2026 PT

[Open the terminal](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/advanced) · [Watch / download the MP4](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/media/43801934433/terminal-30s.mp4) · [Video manifest](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/media/43801934433/manifest.json) · [Frame contact sheet](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/media/43801934433/contact-sheet.png).

The exported film is exactly **30.0 seconds**, **1920×1080**, **30 fps**, H.264, silent, at **2×** the actual 60-second exploration. All **37 submitted series** were visited. Right-side controls change rental assumptions, horizon, historical anchor, GPU-hours and the separate hardware-resale index. The 58-entry trace retains their exact timing and states. All video inputs are public API snapshots; their hashes and the unchanged official CSV hash are retained. The input responses and original browser recording are included in the [remote run artifact](https://github.com/howdymary/mochi-demo/actions/runs/43801934433).

The MP4 is 3,940,145 bytes, SHA-256 `2987075a3212fff54d167a0df7e079ce1f132db4e208a0670f34932b3b4f9ff0`. Full-file and HTTP byte-range delivery were verified. The opening frame and six-frame contact sheet were visually inspected; no other desktop content or private sessions appear.

[Implementation](https://github.com/howdymary/mochi-demo/commit/5663bb115e510d49210d96bf6f11349335627d27) · [Source-to-screen report](../results/terminal-v10/runs/43801775647/report.json) · [Desktop](../results/terminal-v10/runs/43801775647/1920-benchmark.png) · [Scenarios](../results/terminal-v10/runs/43801775647/1920-scenarios.png) · [Mobile](../results/terminal-v10/runs/43801775647/390-benchmark.png).

The terminal passed exact forecast agreement, historical identity/cutoff/gap checks, scenario arithmetic, saved-point immutability, keyboard/touch and overflow checks at 1920px, 1512px, 390px and 320px. Forecast loading also passed with a simulated history-service failure. Deployment passed 165 tests with 3 skips and preserved the protected original export and video workflow.

The first capture request failed before recording because its response callback received the request argument in place of snapshot bytes. [That failed run](https://github.com/howdymary/mochi-demo/actions/runs/43801726740) remains retained; the corrected request is separately versioned. No research experiments or training were rerun.

All eleven browser-validation workflows passed on the deployed source. The earlier Research navigation and memory-panel timeouts were retained and passed one bounded rerun each; numerical and HTTP assertions were not weakened. [Versioned release manifest](../results/terminal-v10/release-2026-11-15.json).

## Current entry point

The main `/terminal` entry is now the [single H100 price canvas](price-canvas-v11.md). This document and its film describe the retained advanced terminal. The earlier capture query keeps that interface; no replacement recording is launched by the canvas release.
