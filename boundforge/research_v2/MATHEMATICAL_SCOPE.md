# Finite-bank composition: standard LP facts and limits

These are standard entropy and linear-programming arguments applied to this implementation.
We do not claim a new theorem.

For each law q_k define N_k=H(X−Y) and D_jk=H(L_j), with L_j in {X,Y,X+Y,X+2Y}.
Independent digit-law counts give entropy sums, after the protected checker verifies injective
balanced-base encoding. Normalized nonnegative counts are therefore a composition variable.

For a finite bank, the best real-valued composition ratio equals the linear program

    maximize Σ_k t_k N_k
    subject to Σ_k t_k D_jk ≤ 1 for each of the four projections; t_k ≥ 0.

To see equivalence, scale any nonzero composition by its largest denominator entropy.
Conversely a positive optimum must have some tight denominator constraint, since otherwise
all coefficients could be increased. Integer counts approximate positive real coefficients
arbitrarily well; the final program rationalizes counts and verifies the actual finite certificate.

The optimum is bounded by 2: for every law,
H(X−Y) ≤ H(X,Y) ≤ H(X)+H(Y).
Columns with all D_jk=0 have N_k=0 and can be removed.
Each remaining variable is bounded by 1/max_j D_jk, so the finite feasible polytope is compact.

An optimal vertex can use at most FOUR positive laws. If more than four coefficients were positive,
their four-dimensional denominator columns would be linearly dependent. A sufficiently small
positive and negative perturbation along that dependence keeps all inequalities and nonnegativity,
contradicting extremality. This does not say two laws suffice, or that our bank contains a globally
optimal law.

The finite-bank dual minimizes Σ_j ν_j subject to ν≥0 and Σ_j ν_j D_jk ≥ N_k for bank laws.
A candidate with positive F(q)=N(q)−Σ_jν_jD_j(q) violates that particular dual constraint.
It is a useful proposal score. A violated optimal dual does not by itself guarantee strict primal
improvement when the optimum is degenerate: another optimal dual might remain feasible.
Re-solve the bank and independently check the resulting exact certificate.

A numerical dual that bounds a finite bank is NOT a proof for all finite random variables.
A numerical F≤0 across tested laws is NOT a global upper bound, nor proof of optimality.
The current stationary-system multipliers are proposal weights, not a universal certificate.

Graph supports (d+y(d),y(d)) ensure X−Y=d is injective. They intentionally restrict the pilot.
Only translation/common scaling can be used without further proof of projection preservation.
No arbitrary GL(2) reduction is assumed.

No result here upgrades a valid lower-bound witness into a proof of the sharp C3c constant.
