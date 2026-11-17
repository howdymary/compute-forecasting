# Direct probability forecasting v18

[Methods](../../docs/direct-probability-v18.md) · [Measured findings](../../docs/probability-v18-findings.md) · [Immutable current report pointer](latest.json).

Audit and run directories retain their source hashes, successful and failed configurations, forecasts and probability vectors. The current pointer advances atomically; older results remain unchanged. Future model-lock and readiness receipts live under future/. PNG-only interface verification lives under validation/.

Verify public arithmetic without provider credentials:

    PYTHONPATH=src python scripts/verify_probability_v18.py

Training may still be running; consult the findings and Actions execution for actual completion. Prospective improvement is not established.
