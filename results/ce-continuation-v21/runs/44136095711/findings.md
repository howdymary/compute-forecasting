# Categorical continuation v21 findings

Post-event historical development and exploratory evaluation. Prospective improvement is not yet established.

A is the frozen operational v19 price-only checkpoint30. B and C share that same initial weights and Adam state, unchanged19-level categorical output and CE objective, lower learning rate and additional update budget. B uses the original corpus; C uses the expanded corpus.

| Corpus | Windows | Horizon examples | Groups | Providers | Origins | Changed7d windows |
|---|---:|---:|---:|---:|---:|---:|
| same | 314 | 942 | 12 | 8 | 90 | 57 |
| expanded | 3837 | 11511 | 48 | 8 | 143 | 1036 |

Expanded-data readiness: True. Reasons: []. Actual selected training sources: {"afhubbard": 3837}.

| Arm | Ordering seed | Additional updates | Selected additional update | Dev7d loss | Exploratory7d loss | Coverage | Mean width |
|---|---:|---:|---:|---:|---:|---:|---:|
| incumbent | 17 parent | 0 | 0 | 0.008652142545484801 | 0.015557662085394464 | 0.8333333333333334 | 0.11702519456317836 |
| same | 17 | 100 | 20 | 0.007938938958549805 | 0.01808340014780294 | 0.75 | 0.06719054018637229 |
| expanded | 17 | 100 | 50 | 0.008182590288285793 | 0.01842522443956998 | 0.75 | 0.05621136844341108 |

Development expansion gate: {"passed": true, "passing_arms": ["same", "expanded"], "incumbent_loss": 0.008652142545484801, "development_losses": {"same": 0.007938938958549805, "expanded": 0.008182590288285793}, "data_effect_screen": false, "threshold": 0.98, "statistical_claim": false}. This is an engineering screen, not statistical evidence.

Only saved development checkpoints select candidates. Exploratory results cover24 seven-day cases on three reused, dependent dates. Seeds share market outcomes. A continuation gain does not isolate learning rate; an expanded-data gain does not isolate sample count from changed corpus composition.

All original training tasks and evaluation cases are preserved. New examples are not independent market experiments; overlap, repeated flat contexts and source variation remain explicit in audit.json.

The operational future candidate is chosen using development scores, with ties retaining the incumbent. Existing panels and gates remain unchanged. Full future probability vectors require compatible fresh source observations and verified pre-resolution publication.

Public arithmetic: python -m compute_forecast.verify_continuation_v21. See docs/ce-continuation-v21.md.
