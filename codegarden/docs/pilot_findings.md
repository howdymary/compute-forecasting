# Pilot findings

Twelve from-scratch constructions were verified. Plain random ordering gave 145–146 words; the tested small-descendant priorities gave 190–192. These are twelve seeded trials, not bounds on those methods.

Four 60-cycle pilot searches (fixed/adaptive, seeds 17/29) retained the verified 226 incumbent. They consumed unequal time and are integration pilots, not an equal-runtime efficacy comparison.

An initial logging attempt exceeded the transport output limit and was not retained as a complete experiment artifact. The pilot was rerun with compressed full logs; only the complete rerun is reported. The adaptive reward was corrected to use improvements over the retained best, rather than rewarding recovery from an accepted downhill state.

Next hypothesis: exact union repairs and larger structural neighborhoods may escape the small plateau; small-neighborhood failures apply only to their hashed candidate pools.
