# Quantile-head failure analysis

The frozen pilot completed 64 updates. On 24 seven-day cases across three reused, dependent dates, selected-head loss was 0.02287759 versus 0.01555766 for its categorical parent. It failed the registered development expansion gate. The incumbent was retained.

Almost all additional loss came from the nine changed-price cases (eight declines and one increase). The 15 unchanged cases had negligible absolute errors, but microscopic one-sided misses in extremely narrow intervals explain why literal coverage was low even there.

The q10, q50 and q90 contributions to trained-minus-parent mean pinball were +0.00774203, +0.00058503 and -0.00100713. They sum to +0.00731993. The upper quantile helped slightly while the lower quantile deteriorated substantially.

The selected head's seven-day interval covered 2/24 outcomes and had mean width 0.00026079 USD per GPU-hour, versus parent coverage 20/24 and width 0.11702519. All nine changed outcomes lay outside the head's interval. This describes a persistence-like, extremely concentrated forecast; it does not establish which training mechanism caused that behavior.

The head interface's own update-zero loss was 0.03790731. Improving from that starting point did not make it better than the original representation. Raw internal head coefficients are not predictive probability mass.

The next modeling proposal should explicitly test preservation of unchanged-price mass and useful downside quantiles, with fixed controls and future evaluation. More updates, another seed or a different prompt are not established remedies. No new optimization was run for this diagnosis.

The figure shows contributions scaled by 1/3 and averaged across all 24 primary cells. Positive means worse. Every value is reconstructed from the source report recorded in diagnostics.json. These are post-hoc historical observations, not prospective improvement.
