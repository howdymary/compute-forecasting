# Joint row-column Hadamard pilot

2026-11-15 UTC. Target: an actual Einstein Arena leaderboard record for problem27, not an unrestricted mathematical claim. Previous block run43766049167 found no improvement in2550 row/column pairs and284598 three-row repairs in180seconds.

## New hypothesis

A row-only or column-only optimum may escape through a coupled row+column update. For the fixed50x50 complement B and border r,c,a, det(A)=±det(B)(a-r B^-1 c). The corresponding inverse entry p=(A^-1)[j,i] gives absolute determinant ratio |p| |a-r B^-1 c|. For a fixed binary c, optimize r=sign(B^-1 c) and a=-1. Alternating r and c optimizes this bilinear objective monotonically up to ties, but does not prove a global optimum. Recover B^-1 from the full inverse with a rank-one Schur update, skip singular complements, and test the identities against exact small determinants before the real run.

The240second pilot visits row-column pairs in seeded random orders with64 binary starts per pair,40 alternating steps maximum. It may alter up to101matrix entries at once. Floating inverses propose; SymPy Bareiss and the independent Fraction Gaussian determinant must agree on every accepted gain, and the official score must exceed the freshly fetched leader. No absence theorem is inferred from failure. A mathematical candidate still needs independent acceptance and live Arena evaluation before a leaderboard-record claim. All changes are scoped to codegarden/ and its approved isolated launcher.
