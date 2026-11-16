# GPU pricing terminal v10

The [full-screen terminal](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal) follows the supplied dark financial-chart reference: a source-separated GPU watchlist, dominant precise price chart, derived lower panels and a right-side variable panel. The original Explore/Research views remain available from Overview.

The terminal reads only the existing verified pricing and approved history APIs. Actual submitted q10/q50/q90 values, the November 6 cutoff, missing historical days, units and exact target identity are preserved. Daily price changes require consecutive observations; there is no volume or OHLC fabrication. The optional EMA 20 is descriptive, resets at gaps and requires 20 consecutive observations. It does not change forecasts.

Rental and hardware-resale scenarios remain distinct assumption calculations. Index 100 is the default. Rental-dollar mode uses the explicitly dated last approved matching historical rate, and is disabled without that anchor. Monthly compute spending is the calculated rate multiplied by user-selected GPU-hours; it is not realized revenue. Rates compound monthly as start * (1 + annual change)^(month/12), or index 100 * (1 - depreciation)^(month/12) for resale.

Source and saved-point drawers retain exact identities, original values, input assumptions, artifact links and the official CSV checksum. No new training or accuracy claim is introduced.

## Recording

A separate requested recording workflow captures an actual 60-second browser exploration and encodes 30 seconds at 2× speed, 1920×1080, H.264. It uses only frozen public API responses, with their hashes retained, and labels the capture as recorded exploration. The tour covers all submitted series and then changes the right-side scenario assumptions. Parameter changes generate explicit calculations; they do not alter archived forecasts.

Recording is initiated only by a committed request configuration or manual dispatch. Existing video files and recording workflows remain unchanged. The new MP4 is versioned separately, with a source-state trace, ffprobe duration, frame checks and hashes. It is published only after numerical and visual checks.

Implementation references: [Playwright Python video recording](https://playwright.dev/python/docs/videos), [FFmpeg setpts](https://ffmpeg.org/ffmpeg-filters.html#setpts_002c-asetpts), [Modal Volume upload and reload](https://modal.com/docs/guide/volumes).
