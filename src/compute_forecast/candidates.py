from itertools import product
from .contracts import Candidate


def candidate_grid() -> list[Candidate]:
    return [
        Candidate(representation=r, composition=c, window_days=w, alpha=a)
        for r, c, w, a in product(
            ("level", "log"),
            ("target_only", "raw", "fixed_basket"),
            (28, 56),
            (1, 100),
        )
    ]
