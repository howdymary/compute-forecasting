# Kakeya pilot002 and C2 fallback — 15 November 2026

No new record was found in the two Kakeya batches.

Pilot002 source `27b024422bc6be0b09d484251582ec5a21b9fd44`, [run43761025827](https://github.com/howdymary/compute-forecasting/actions/runs/43761025827), artifact head `92177523a8f402c546199b907ef4321d62a9fd80`, returned the same0.10675138995168142 incumbent from all six600-second workers. There were139 completed local trials and57,551 native evaluations.

Deeper refinement resolved the prior truncation concern:120 local solves returned convergence status0,19 reached a limit. None beat the starting point. The initial native gradient infinity norm was approximately6.22e-15. This supports stopping these tested strategies; it does not prove local or global optimality. Uniform-block and baseline-band/resizing policies both failed to improve within their explicit budgets. Tinker selected aligned resizing after retrieving the analyst's prior negative finding through past.dev. The model was untrained; no policy gain is claimed.

The Kakeya pilot is ended early rather than spending its entire two-hour maximum. Its frozen exact verifiers, witnesses and experiments remain unchanged. No further deletion-code searches were launched.

## Fallback preparation

The CPU-only [C2 preflight43762149905](https://github.com/howdymary/compute-forecasting/actions/runs/43762149905), source `438038307863053bb7195498b810e53241d8aca1`, reproduced MLAI_YONSEI solution2783 with1,999,999 values:

- Live Arena score:0.9636615620620852.
- Reproduced official score:0.9636615620620850.
- Nearby integer construction, exact NTT/CRT score:0.9636615619075807.
- Quantization change:−1.54504e-10, explicitly not a new record.
- Full-size exact certificate time:3.48seconds.
-28 schoolbook/exact-fraction fixtures passed; five invalid-input fixtures were rejected.

The two floating values and the quantized integer construction are different witnesses. The exact certificate proves the latter's rational score, not identity with the floating leader. The preflight artifact contains the original API response, integer JSON/text witness, certificate and dependency provenance.

A first preflight attempt stopped at compilation before any service work because Boost headers were absent. The successful version downloads and extracts the header package under `codegarden/c2/.deps/`, avoiding global environment changes.

## Bounded C2 polish

The new experiment compares fixed and Tinker-selected smooth-max schedules, on the same live baseline and seed with900seconds each. It adapts the [published Dinkelbach optimizer](https://github.com/justinkang221/second-autocorrelation-inequality) at revision `04eba482710e013f14e669be53d6fea89342cc99`, while fixing total mass and the smooth-max temperature within each inner solve. These are empirical nonconvex search methods, not guaranteed global optimization.

An A100-40GB is requested for FP64 FFT work. Actual device and forward-score timings are recorded. A CPU fallback is allowed only on definitive GPU-access denial before any call handle exists; an observation timeout cannot trigger a duplicate search. No cards, purchases, topups, billing settings or account-balance queries are used.

Every returned proposal is converted into a plain nonnegative integer witness and scored by the independent exact NTT/CRT program and the frozen official implementation. A separate job reruns acceptance without the optimizer or provider credentials for any meaningful gain. That job also refreshes the live Arena comparison. Mathematical improvement, the Arena minimum increment and global priority remain separate claims.

No C2 search result is claimed here; this is the experiment's pre-run report.
