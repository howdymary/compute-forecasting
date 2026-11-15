# Attribution and publication scope

Compute Forecast's project source, methods, and measured results are maintained by Mary Liu.

## Data and methodology

- **Pacific Machines (2026), gpu-price-pack v0.1.1-handover** supplies the competition's canonical target definitions, archive manifest, and scoring implementation. The raw compilation is not redistributed. Approved v5 daily target histories are extracted under the current brief's CC BY 4.0 compilation grant and shipped component permissions, with source attribution and changes recorded in [DATA_SOURCES.md](docs/DATA_SOURCES.md). The marketplace-ask history remains withheld.
- **Alex Hubbard, GPU Price Tracker** supplies the independently retrieved historical context under its explicit [CC BY 4.0 data license](https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE). [Changes, coverage, attribution, and limits](docs/DATA_SOURCES.md) accompany the published derivatives.
- Provider/configuration normalization has established precedents, including **Silicon Data** and **SemiAnalysis**. The project does not claim to have invented normalization, compute-price forecasting, or learned experiment selection.
- **Amazon Chronos-2**, revision `29ec3766d36d6f73f0696f85560a422f50e8498c`, is an Apache-2.0 model used for a fixed control. Its weights are not included.
- **Qwen/Qwen3.5-4B** is the base model used by the reported Tinker policy experiments. Access to private trained checkpoints is separate from this repository.

- **Epoch AI hardware** contributes attributed form-factor and power references under CC BY 4.0. **MLCommons results repositories** underpin the pack's Apache-2.0 derived capability ladder. Derived ratios are not official verified MLCommons results; exact contexts and chain notes remain available. MLPerf is a trademark of MLCommons Association.

## Software and visual dependencies

Modal, Tinker and tinker-cookbook, NumPy, pandas, scikit-learn, PyArrow, DuckDB, FastAPI, Starlette, Uvicorn, Pydantic, pytest, Playwright, HTTPX, Exa, and past.dev retain their respective software licenses or service terms. Source-level dependency declarations and resolved remote run environments are preserved.

The interface uses the **Caveat** font from Google Fonts at commit `a85fc09e44c70c7159761adfdc9d5dd007792c15`. It is distributed under the SIL Open Font License; the verified font and license are served together by the application. Charts and interface screenshots preserve exact underlying values.

## Rights

Upstream licenses apply to their respective materials. Data-source attribution and a public repository do not grant a new blanket license over unrelated material. No separate project-wide code license has been declared in this repository.
