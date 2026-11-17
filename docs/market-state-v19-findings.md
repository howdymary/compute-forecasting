# Market-state v19 findings

Retrospective direct forecasting comparison; prospective accuracy is not established.

Training: 314 overlapping windows; 354 actual optimizer updates across six runs.

| Seed | Price-only seven-day pinball | Market context | Market minus price |
|---|---:|---:|---:|
| 17 | 0.015557662 | 0.016692375 | +0.001134713 |
| 29 | 0.016804251 | 0.016347730 | -0.000456521 |
| 43 | 0.013900696 | 0.014964573 | +0.001063876 |

price across three seeds: seven-day pinball 0.015420870, median-price MAE 0.044176717, coverage 84.72%, mean interval width 0.088480102. Selected updates: 30, 30, 30.

market across three seeds: seven-day pinball 0.016001559, median-price MAE 0.045424114, coverage 80.56%, mean interval width 0.065153221. Selected updates: 59, 30, 30.

Lower pinball is better. Seeds share the same market outcomes and are not independent market tests.
Retrospective scope: 24 seven-day cases, three reused dependent origins. Twelve training groups; eight eligible evaluation groups.

Only observed other-provider price changes and collection composition were tested. No evidence of news or availability value follows.

The separate contract-transfer panel starts no earlier than December 20, 2026, uses 16 weekly origins, and has an April 12, 2027 analysis gate.

The experiment is running; prospective improvement is not yet established.
