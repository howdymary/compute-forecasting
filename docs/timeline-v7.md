# Historical prices and archived forecasts

Explore opens on an exact-target calendar joining the licensed v5 historical adapter to the unchanged official forecast CSV. This is a presentation release; frozen numerical studies, protocols and future signal evaluation are unchanged.

## The view

- Ink: actual daily historical medians through November6,2026.
- Cobalt marks and dashed segments: exact submitted1-,3-,7-day medians. The shaded polygon connects submitted q10/q90 values; it does not introduce daily predictions or demonstrate calibration.
- Vertical cutoff: November6,2026,23:59:59UTC. No later competition outcomes are retrieved or plotted.
- Calendar spacing is linear. History and forecast paths never connect across the cutoff. Missing dates break the historical path; flat prices stay flat.
- A2-week,1-month,3-month or all-history control changes the historical window. The overview retains the full available record and has a separate vertical scale, explicitly labeled.

The hero uses the original currency and per-GPU-hour unit. Its vertical axis starts at zero. Exact values are available in the inspector, source disclosure and pinned snapshots. Hover, touch, arrow keys, Home/End and the time ruler inspect real recorded points only.

## Identity and rights

The adapter joins by exact series ID, then verifies source ID, GPU/configuration label, pricing tier, statistic and units. It never substitutes independent Hubbard context or another provider population. The approved v5 adapter contains36 of37 submitted histories,3204 daily observations; the source-register caveat on the remaining marketplace history is preserved. Its submitted forecast remains visible without fabricated history.

Every historical pin retains its observation date, exact value, series ID, unit, source URL, points hash, study revision and frozen compilation vintage. Existing forecast pins retain the official CSV hash. Pins remain unchanged when controls change.

[Publication decisions and component attribution](pacific-value-v5.md) remain authoritative. Frozen historical dates do not establish real-time availability. Raw offer tables are not exposed by this view.

## Loading and reliability

The existing pricing and history requests load independently. Forecasts render immediately while history is loading or unavailable. A visible error/retry state handles failed history loading. No empty region is filled with simulated prices.

## Remote verification

The dedicated timeline workflow checks actual API values, exact target joins, calendar geometry, historical gap breaks, all111 forecast values, unchanged official CSV bytes, immutable pins, source rights exclusions, keyboard/touch behavior, loading/retry and1512/390/320px layouts. PNG captures are retained for visual review; no video is recorded.

After installation on a remote runner:

~~~sh
python -m compute_forecast.validate_timeline_v7
~~~

This interface release was developed after the conservative November15,2026,14:00PT event deadline. It does not alter or replace the pre-deadline official submission.
