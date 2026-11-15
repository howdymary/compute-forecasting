# Second autoconvolution inequality: backup preflight

This CPU-only preflight prepares the fallback selected during the Kakeya pilot. It does not start a GPU search or claim a new result.

It fetches the current official problem and leading explicit construction, requires the live verifier hash to match the pinned source, and reproduces the score. It then quantizes the normalized nonnegative values to integers in0..2^32, recording any score change rather than pretending the approximation is identical.

For integer coefficients a and exact autoconvolution c=a*a, the piecewise-linear integral score is

`(2*sum(c_k^2)+sum(c_k*c_(k+1)))/(3*sum(c_k)*max(c_k))`.

The native certificate uses three prime-modulus NTTs and CRT. It checks primality, supported transform length, root order, a proven bound ensuring unique reconstruction, exact zeroth/first moment identities, and schoolbook agreement on small inputs. The final numerator/denominator are exact integers. The bound on input length and coefficients also protects fixed-width accumulators. Boost uint256 handles the degree-four moments.

Run `g++ -O3 -std=c++17 codegarden/c2/exact.cpp -o codegarden/c2/.build/exact`, then pass a text witness containing n followed by n integers to that executable. No model, API or search history is needed. The GHA artifact contains the plain text witness, JSON integer witness, original Arena response, tests and exact certificate.

The current floating leader and the integer approximation are distinct witnesses. Only a candidate beating a fresh current score by the required margin after independent verification could qualify as a new Arena record. A global claim requires a separate source audit.

Published optimizer research is credited to [justinkang221/second-autocorrelation-inequality](https://github.com/justinkang221/second-autocorrelation-inequality), inspected at revision `04eba482710e013f14e669be53d6fea89342cc99`. No optimizer from that repository is executed by this preflight. It is preparation while the bounded Kakeya experiment continues; no provider balances or billing APIs are queried.
