# Independent Device-State Audit

- Oracle mode: `simulated`
- Note: Simulated mode validates the audit pipeline and file formats; it is not a real-device result.
- Routines: 30
- Paired runs: 150
- Overall agreement: 100.0%

| Dataset | Routines | Paired Runs | Device State | Platform State | Routine Match | Event Match | Exception | Lifecycle | Timing-only | Agreement | Vendor API Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| long-chain | 10 | 50 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 35.29% |
| smart-home | 20 | 100 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 85.0% | 100.0% | 37.8% |
