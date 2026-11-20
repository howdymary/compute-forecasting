# V17 memory review recovery

Training and all physical evaluations finished in [run 44699655265](https://github.com/howdymary/mochi-demo/actions/runs/44699655265). Its final past.dev handoff stopped when recall did not return the required source ID. The source had completed ingestion. The failed recall remains recorded and is not counted as a successful handoff.

The original result content was 72,018 characters, approximately 18,005 evidence tokens. Recall requested the 16,000-token medium budget. Past.dev documents that whole documents can be omitted when they exceed the evidence budget, and that plans can impose a lower ceiling. This is a likely explanation, rather than an isolated causal diagnosis. [Official recall contract](https://past.dev/docs/memory-api/api-reference#post-api-v1-recall).

The recovery wrote an 8,247-character semantic summary. It retained exact outcomes, failure locations, source IDs, hashes and a reference to the full artifact. Exact measurements and trajectories stayed in the artifact layer. The resumed read used an 8,000-token budget, the original reader identity and an exact returned-source check. It omitted the original exact occurrence-time window. Both retrieval changes are disclosed; their individual effects were not ablated.

The first review-only attempt, [44734727709](https://github.com/howdymary/mochi-demo/actions/runs/44734727709), stopped during local validation because the inherited adapter imported robot meshes. It made no provider calls and debited no experiment budget. The corrected adapter imports neither the robot world nor MuJoCo.

[Run 44735240968](https://github.com/howdymary/mochi-demo/actions/runs/44735240968) completed the actual handoff:

1. The experimenter wrote the compact numerical evidence.
2. The critic recalled its source ID and used the evidence in a bounded model decision.
3. The critic wrote a qualified rejection, which the researcher recalled.
4. The researcher selected policy-generated laptop states as the next research focus and searched Exa.
5. The researcher wrote the sourced proposal. The designer recalled it and selected laptop-contact state collection as a future investigation.
6. A private critic canary was denied to the designer through the existing audience controls.

The follow-up investigation is advisory. No new controller, optimizer update or physical experiment was executed. The review does not turn a failed robot evaluation into a successful one.

Four writing identities and four verified readers completed six cross-role recalls within V17. The separately logged cross-run recall remains separate. All ingestions finished, and the private-audience test passed. The original oversized record and its failed recall remain in the provenance chain.

The result digest before and after recovery was:

```text
879144b8d8e8ddabcb8cad86ac74661cf4b9575f7dc3ce1c6db0f511a5914432
```

Twenty-three retained numerical input files were byte-identical. The shared ledger remained at 223 accounted attempts/stages, 221 completed attempts/stages, 14.8859005845 accounted CPU-hours and 16 optimizer updates. Memory, search and advisory inference counters advanced within the existing limits. No resource counter was reset.

Implementation: [memory-only adapter](../src/mochi/smooth_v17/finalize_memory.py) and [additive review workflow](../../.github/workflows/mochi-smooth-v17-finalize.yml). The frozen training and simulation source remained unchanged.
