# Development checkpoint 1

The first trained checkpoint and the parent both completed scenario 212002 within every quality limit. The parent used 436 steps and 283.319 simulated seconds; checkpoint 1 used 420 steps and 277.031 seconds. Recovery joint travel fell from 20.939 to 15.860 radians, approximately 24.3%. This is one paired development case, not a fresh-test result.

The only changed discrete choice in this pair was the clock approach, F to H0. Walking remained W10 and recovery remained R4 at every station. Earlier task actions affect the physical states reached later in the sequence. These observations do not establish that the native gait was trained or isolate the effect of the clock change from simulator variability. Tinker updated the shared selector, with actual gradient calls for all six domains.

Both policies still failed during laptop contact on scenarios 212000 and 212001. The preview retains those failures. Checkpoints 4 and 8 are undergoing physical evaluation; selection and fresh tests remain pending.

[Paired measurements](../evidence/paperfree-v19r1/development-update1-paired.json) · [Continuous browser verification](../evidence/paperfree-v19r1/development-preview-browser-qa.json)
