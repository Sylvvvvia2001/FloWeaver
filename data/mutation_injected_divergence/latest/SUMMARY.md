# Mutation-Injected Divergence Analysis

- Oracle mode: `synthetic_mutation_replay`
- Note: Synthetic semantic-breaking traces are fed through the existing M6 TrustLayer; this does not execute real Home Assistant routines.
- Routines: 30
- Valid injected mutations: 150

## Overall

| Scope | # Mut. | MRR | FPR | CEY | Trace-only Reject | VTA |
|---|---:|---:|---:|---:|---:|---:|
| long-chain | 39 | 100.0% | 0.0% | 69.23% | 30.77% | 100.0% |
| smart-home | 111 | 100.0% | 0.0% | 74.77% | 25.23% | 100.0% |
| Overall | 150 | 100.0% | 0.0% | 73.33% | 26.67% | 100.0% |

## By Mutation Type

| Mutation Type | # Cases | MRR | FPR | CEY | Trace-only Reject | VTA |
|---|---:|---:|---:|---:|---:|---:|
| Dependent-action swap | 20 | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| Premature state writeback | 20 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| Missing refresh/status query | 20 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| BLE serialization violation | 12 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| Cloud rate/session violation | 18 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| Wrong batching/writeback merge | 20 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| Same-device ordering violation | 20 | 100.0% | 0.0% | 0.0% | 100.0% | 100.0% |
| Cleanup/lifecycle violation | 20 | 100.0% | 0.0% | 100.0% | 0.0% | 100.0% |

## Detection Evidence

| Evidence Type | Count |
|---|---:|
| counterexample verdict: DIFF_FOUND | 110 |
| counterexample verdict: TRACE_ONLY | 40 |
| validator diff kind: missing_prerequisite | 38 |
| validator diff kind: order_violation | 112 |

## Coverage

| Coverage Type | Count |
|---|---:|
| modality: BLE | 8 |
| modality: BLE+Cloud | 10 |
| modality: BLE+Local+Cloud | 22 |
| modality: Cloud | 43 |
| modality: Local | 50 |
| modality: Local+Cloud | 17 |
| latency group: G1:(0,3] | 49 |
| latency group: G2:(3,6] | 15 |
| latency group: G3:(6,9] | 45 |
| latency group: G4:(9,+) | 41 |
