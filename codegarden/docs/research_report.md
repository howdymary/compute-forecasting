# CodeGarden research report — work in progress

## Mathematical result

Best independently verified witness: 226 words, **reproduced**, not newly
discovered. It matches kgrey's arena submission 2778.
Canonical witness SHA-256:
417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa

Target: 227 provisionally, based on the live leaderboard capture at
2026-11-15T02:47:10Z (November 14 in America/Los_Angeles).
Recheck the arena before any submission or record claim.

## Comparisons that must remain separate

- Historical CPro1 construction: 208, reproduced from both the pinned author
  result and the arena download; exact witness equality confirmed.
- Weindel–Heckel v2: 215 from KaMIS is a reported finite-length lower bound;
  200 is one of the authors' own search rows, and 487 is a reported LP upper
  bound. These are different results.
- Current arena capture: 226. Five leading/historical witnesses were retrieved
  and independently checked.
- Global record: not certified. Targeted current search and primary papers were
  checked; newer asymptotic deletion results do not automatically supply a
  better explicit length-16 witness.

## Verification

The official statement and source verifier were retrieved from the public
problem API. Its conventions agree with distinct within-word descendants and
cross-codeword collision rejection.

The independent string verifier and independent LCS dynamic program agree on
the 226 code. The latter checks 25,425 distinct pairs and maximum LCS 13.
The official verifier separately returns 226. Ten initial verifier tests pass;
search and shared-budget tests raise the current total to eighteen.

The packed representation contains all 65,536 candidates, all 16,384 descendants,
and 2,244,608 deduplicated incidences. Precomputation took about one second in the
recorded in-memory pilot. Three hundred length-16 samples agreed with the simple
string implementation, and small-length agreement is exhaustive.

## Experiments completed

- Twelve seeded constructions from scratch: random ordering 145–146;
  tested small-descendant priorities 190–192; other priorities 159–182.
  These tiny samples are not method bounds.
- Four 60-cycle fixed/adaptive integration pilots: best 226, no improvement.
  Unequal consumed runtime prevents an equal-time efficacy claim.
- A three-second fixed/adaptive pair, seed 43: both 226; 221 versus 71 cycles.
  This single pair does not establish comparative efficacy.
- Twenty-one exact bipartite-union combinations: no improvement over their
  better input. Matching/vertex-cover certificates prove union optima only.
- Complement and reversal were checked against D2 for every length-16 word.
- First hosted CPU batch: 1,200 cycles, best 226, both independent checks pass.
  Execution: https://github.com/howdymary/compute-forecasting/actions/runs/43670274708
- An expanded hosted CPU batch is running. Do not report its result before its
  exported witness and verification receipts arrive.

## What changed

The system now records exact neighborhoods and distinguishes exhaustive
encoded-pool failures from timeouts. An initial operator reward that counted
recovery from downhill states was corrected to count improvements over the
retained best. Full logs are compressed after a transport-size failure; the
complete rerun, rather than a truncated transcript, is the retained pilot.

Search methods include greedy priorities, randomized and structural destruction,
conflict/opportunity selection, forced ejection pivots, bounded exact repairs,
and exact bipartite fusion. Sparse CP-SAT is prepared as a larger-neighborhood
comparison.

## Autonomous-loop and sponsor status

The executed adaptive policy is a deterministic empirical controller. It is not
an LLM research loop. No Tinker adaptation gain is claimed.

The sponsor adapters and read-only account checks are separate from evidence of
live use. Existing forecasting sponsor activity is not counted as CodeGarden
activity. Prepaid balance/shared-reservation interpretation remains a distinct
gate. No credit purchases, replenishment, plan changes or interference with
another project's jobs occurred.

Outstanding requested evidence: genuine CodeGarden Exa-driven decisions,
multiple real past.dev role writers/readers with causal reuse, actual Modal
search workers, and a before/after Tinker evaluation on fresh seeds.
Those are incomplete until live receipts exist.

## Limits

No 227-word code has been found. No global optimality proof is claimed.
Neighborhood certificates say nothing about codes outside those neighborhoods.
The protected supervisor hashes verifier source before accepting exports;
the model proposer has only a bounded JSON action interface. This is an
application trust boundary, not an OS sandbox for arbitrary adversarial code.
