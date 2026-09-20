# Fair action-level baseline simulation v2

This dataset supersedes the earlier separately calibrated HEFT and NaiveTopo
figure inputs. Both methods use the same basic action DAG, targeted HA
writeback edges, same-device serialization, and coarse protocol budgets.

- HEFT uses upward-rank earliest-finish scheduling.
- NaiveTopo uses stable greedy topological batching.
- Both are validated in check-only mode and do not invoke rollback.
- `rr1_pct`, `rr2_pct`, `rr3_pct`, and
  `mean_diagnostic_rollback_depth` are counterfactual repair-demand metrics.
- Latency statistics include only validation-passed routines.
- Values are deterministic simulation outputs, not device measurements.
