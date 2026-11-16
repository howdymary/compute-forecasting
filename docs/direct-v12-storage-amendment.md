# Direct v12 checkpoint storage amendment

The original seeds 17 and 29 each completed 100 optimizer updates. Free checkpoint storage interrupted sampler creation, and seed43 was refused before training-client creation. The user authorized removal of the four untrained update-zero storage copies; baseline identity and all numerical baseline evaluations remain retained. All learned states and older frozen studies remain.

Seed43 uses the same data, model, renderer, seed, optimizer, minibatch order, update count, sampling budget and development-only selection rule. Its storage implementation retains optimizer states at 20/50/100 and uses fixed ephemeral sampling clients instead of duplicate persistent sampler copies. Update zero remains the unadapted public model and its retained baseline evaluation. This changes resource retention, not the forecasting algorithm. Earlier runs keep their original implementation and provenance.

The reference export correction uses the unmodified official baseline script with explicit fixed series IDs, preserving all previously emitted numerical values. Missing comparator rows do not remove difficult model-evaluation cells. The earliest complete retained model predictions are reused for finalization; no model score is improved by repair.
