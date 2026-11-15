# Comparative review: is BoundForge on the right path?

Research date: November 14, 2026, America/Los_Angeles. Discovery receipts use UTC.
Primary-source review plus ten actual Exa queries. A search miss is not evidence of novelty.
Research phase launches no Tinker inference/training or Modal compute.

## Conclusion

Retain C3c, but stop using tail extension as the main discovery strategy.
The current certificate is correct; its tiny gain and four model selections do not establish
a substantial mathematical advance or a superior autoresearch method.
Investigate diverse new laws and their complementary entropy vectors. Give the model an opportunity
to propose constructions outside the deterministic insertion menu. Keep numerical scoring and
certification deterministic. Do not fine-tune yet.

## Comparative evidence

| Project / primary artifacts | Representation, research loop and human contribution | Result and verification | Transfer and limits |
|---|---|---|---|
| [FunSearch, Nature 2023](https://www.nature.com/articles/s41586-023-06924-6); [official code](https://github.com/google-deepmind/funsearch) | Evolve a priority program inside a human-specified construction/evaluator; retain scored programs in an evolutionary population. | Released cap-set constructions and evaluators can be replayed. Repository omits the generation models, execution sandbox and distributed infrastructure. | Search over useful programs rather than ask a model to pick among fixed moves. Replaying a released program is not reproducing discovery. Dollar cost not established from inspected artifacts. |
| [AlphaEvolve mathematics study, v3](https://arxiv.org/html/2511.02864v3); [system paper](https://arxiv.org/html/2506.13131v1) | Evolve bounded search procedures, not just candidate objects. Humans specify objectives and interpret outputs. | Reports results across 67 problems, including arithmetic Kakeya, with successes and failures. Model/evaluation-cost ablations are reported. Exact mathematical conclusions require problem-specific checking. | Amortize a model call over substantial numerical search. Do not equate more parallelism with more efficient discovery. Full-system compute is not our budget; no full reproduction claimed. |
| [PatternBoost](https://arxiv.org/html/2411.00566v1); [author code](https://github.com/zawagner22/transformers_math_experiments) | Alternate classical local optimization with training a transformer on strong constructions; sample new seeds and polish them. Humans design encoding and local search. | Several extremal constructions; performance varies by problem. The illustrative triangle experiment exposes invalid model outputs and the value of subsequent repair. | First build a diverse, meaningful archive. Four almost-identical insertion choices are not a training corpus. Published illustrative training uses 15,000 steps; our adaptation would need separate justification. |
| [Wagner, 2021](https://arxiv.org/pdf/2104.14516); [author repository](https://github.com/zawagner22/cross-entropy-for-combinatorics) | Encode finite objects as sequential decisions and train with the deep cross-entropy method; human supplies objective and representation. | Explicit conjecture counterexamples; paper also gives LP-derived results. It reports difficulty of sparse-reward alternatives. | A classical elite-distribution method is an important baseline. A large pretrained LLM is not necessary for every construction problem. No compute-equivalent reproduction claimed. |
| [AlphaTensor, Nature 2022](https://www.nature.com/articles/s41586-022-05172-4); [official artifacts](https://github.com/google-deepmind/alphatensor) | Tensor decomposition as a single-player search/RL game; humans define tensor, arithmetic and training. | 4×4 multiplication in characteristic two with 47 scalar multiplications versus 49 for Strassen-square. Released decompositions permit exact checking; this is not the same result over the reals. | Define the mathematical domain precisely and publish witnesses separately from search. Repository release is not a complete training-system reproduction. Training dollars unknown here. |
| [Ajwani et al., 2026 PatternBoost study](https://arxiv.org/html/2610.19980) | Compare representations, local moves and surrogate evaluators in three geometry problems; add expert-structured seeds after plateaus. | Reports square-stabbing gaps 20/13 automatically and 14/9 with a staircase construction. 81 configurations, one run each and 24-hour budgets; authors identify descriptive, not replicated, marginals. | Direct warning against expecting generic training to overcome poor representation. We should use repeated seeds and report expert input. The arXiv abstract reports acceptance at ALENEX 2027; the result is not independently reproduced in our project. |
| [Green–Ruzsa](https://arxiv.org/html/1712.02108); [Tao's subsequent explanation](https://terrytao.wordpress.com/2025/11/19/sum-difference-exponents-for-boundedly-many-slopes-and-rational-complexity/) | Entropy/projection formulations supply the mathematical objective; computational examples can reveal structure that needs a subsequent proof. | These are mathematical arguments, not benchmark demonstrations. Tao distinguishes modest numerical gains from the more informative asymptotic pattern inspired by constructions. | Look for an explanatory construction principle. We retain C3c; auxiliary families must not silently replace the requested target. |
| [Jaswal exact certificate](https://zenodo.org/records/23289305); [current C3c table](https://teorth.github.io/optimizationproblems/constants/3c.html) | Two complementary finite laws, independent digit composition, stationary free-energy/Newton optimization, rational rounding and checking. | Published exact witness about 1.67489421130711622876434373706. Table records independent replay. | Our inherited method and almost all bound magnitude are attributable here. Reoptimizing this construction is adaptation, not a new framework invention. Exact support geometry and complementarity are the relevant starting points. |
| [Tomar upper-bound manuscript](https://www.mefyi.com/papers/sum-difference-exponents/sum-difference-exponents.pdf) | Search for rational combinations of entropy inequalities using LP; author supplies proof construction and formalization. | Manuscript claims improved C3b/C3a bounds and Lean proofs; we have read the statement but have not reproduced its Lean build. | Useful numerical/verification precedent, NOT a C3c lower-bound improvement. Do not conflate an LP certificate for a finite witness with a universal entropy inequality proof. |

## Four closest methodological lessons

**FunSearch:** Human-designed scaffolding is crucial. The released notebook allows a clean diagnostic:
constant priority versus the published priority and random priorities under the same greedy builder.
Our replay uses a pinned commit and an independent exact pair checker. It tests representation and
released artifacts, not the historical LLM run. Report measured outputs in evidence/funsearch-replay.json.

**AlphaEvolve:** The paper explicitly motivates evolving a search algorithm when object scoring is cheap:
one expensive model call should drive many cheap trials. Our four-way insertion menu cannot test that
claim. A bounded construction-program language is a feasible first adaptation, but is more restrictive
than full-file evolution and must be labeled accordingly. The study also reports model and parallelism
tradeoffs; no universal cost advantage follows.

**PatternBoost / subsequent geometry study:** A useful global learner depends on the quality and diversity
of locally optimized training instances. Representation and expert initialization can dominate outcomes.
Our present archive is concentrated around two laws. Generate and optimize new families before deciding
whether there is enough data to train. Preserve invalid outputs and rejected constructions.

**C3c literature:** Our numerical improvement must be compared with the underlying high-precision
two-law stationary solution, not merely the rounded 15-digit bound. Independent-digit composition
adds entropy vectors; it does not mix probabilities. A positive finite-bank LP result is a valid
candidate construction only after rationalization and interval verification. A nonpositive numerical
oracle result does not prove global optimality or a universal dual bound.

## Originality assessment

Established prior art: evaluator-guided evolution, local/global alternation, elite archives, numerical
polishing, entropy objectives, independent-digit composition and two-checker certificates.

Adaptations worth testing: bounded model-written construction programs; dual-guided search for
complementary laws; explicit multi-law bank with deterministic optimization and exact certification.

Not yet established: a new C3c construction family, a useful theorem, superiority over numerical
search, memory benefit, training benefit, or a substantial new best-known lower bound.

Engineering changes alone do not make the result mathematically publishable.

## Source quality and gaps

Use original papers and author repositories over launch summaries. The latest inspected AlphaEvolve
mathematical version is v3 (December 22, 2025). The current C3c table still lists Jaswal's bound and 1.75
as the upper bound; our private refinement is not listed there. A newly discovered upper-bound
manuscript concerns different constants and is labeled as a claim pending reproduction.

The Jaswal Exa query returned irrelevant thermodynamics pages; use the exact archived certificate,
not those search hits. Other secondary search hits are discovery aids, not evidence.
Several systems do not release their complete training/discovery infrastructure or itemized costs.
No independent reproduction is claimed for an unexecuted paper result.
