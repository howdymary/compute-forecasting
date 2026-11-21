# Laptop contact-location diagnostic

This local diagnostic ran separately from the frozen paper-free training study. It replayed checkpoint 4’s recorded choices to reach a laptop approach on development condition 212000, saved the full physical state, and compared four contacts from that same state. No Tinker updates were performed and no existing controller or evaluator was edited.

| Contact | Radius from hinge | Desk x | Laptop closed | Final opening | Peak contact force |
| --- | ---: | ---: | --- | ---: | ---: |
| Existing P5 | 0.150 m | 0.263 m | No | 1.221 rad | 0.698 N |
| Lower, inset A | 0.140 m | 0.258 m | No | 1.239 rad | 0.829 N |
| Lower, inset B | 0.135 m | 0.255 m | No | 1.234 rad | 0.738 N |
| Lower, inset C | 0.140 m | 0.255 m | No | 1.235 rad | 0.724 N |

The first candidate exceeded the unchanged 0.8 N force limit and stopped early. The others remained unsuccessful. Moving the contact inward and lower did not resolve this failed approach; none was accepted. The diagnostic stopped after five physical attempts, including prefix generation, using approximately 359 single-thread wall seconds, below its eight-attempt and 1800-second cap. Exact timings and artifact hashes are in the [measurements](../evidence/contact-geometry-v20/results.json).

Restored branches are useful for testing a contact hypothesis but do not demonstrate continuous four-task success or a training gain. The local replay also does not establish bitwise identity with the cloud rollout. The current Tinker comparison retains its original geometry, controls, qualification limits and test cases.
