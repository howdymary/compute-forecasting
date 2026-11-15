# CodeGarden C2: exact certificates and bounded polish

The CPU preflight reproduces the current Second Autocorrelation leader and certifies a nearby integer construction. It starts no remote optimization itself. `polish.py` adds a bounded Modal search; actual hardware, errors and any fallback are recorded.

The objective is the **autoconvolution** ratio. For explicit integer coefficients a and exact c=a*a, its piecewise-linear integration score is exactly

`(2*sum(c_k^2)+sum(c_k*c_(k+1)))/(3*sum(c_k)*max(c_k))`.

`exact.cpp` uses three NTT primes with checked roots, a proven unique-CRT coefficient bound, exact moment identities and small-instance schoolbook checks. It returns an exact integer numerator and denominator. `official.py` is the pinned Arena implementation. `manifest.json` freezes both verifier sources.

The standalone exact command needs no model, API or search history:

```sh
mkdir -p codegarden/c2/.build
g++ -O3 -std=c++17 -Icodegarden/c2/.deps/boost/usr/include codegarden/c2/exact.cpp -o codegarden/c2/.build/exact
codegarden/c2/.build/exact < integer_witness.txt
```

The dedicated workflows extract Boost headers under codegarden, create an isolated Python environment, and preserve plain JSON/text witnesses in their downloadable artifacts. Large search checkpoints live in a dedicated CodeGarden Modal volume. GitHub metadata carries hashes and exact certificates.

Search adapts [published C2 methods](https://github.com/justinkang221/second-autocorrelation-inequality) inspected at `04eba482710e013f14e669be53d6fea89342cc99`. Its floating FP64 objective only proposes candidates. Fixed mass and fixed inner smooth-max temperature control scale drift. No convergence-to-global-optimum or trained-policy advantage is assumed.

An Arena lead requires comparison against the fresh live leaderboard; a global-record claim requires an additional literature/source audit. Quantized approximations are identified as distinct witnesses. No billing dashboards, purchases or account-setting changes are authorized or used.
