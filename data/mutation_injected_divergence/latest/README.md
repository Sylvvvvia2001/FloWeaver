# Mutation-Injected Divergence Analysis Files

This directory contains a local synthetic replay of semantic-breaking mutations through the existing M6 TrustLayer.

- `experiment_config.json`: run configuration and false-positive definition.
- `mutation_manifest.csv`: selected routine/mutation pairs before validation.
- `mutation_results.csv`: one row per injected mutation with validator verdict and counterexample fields.
- `summary.json`: machine-readable aggregate metrics.
- `SUMMARY.md`: paper-facing summary tables.
- `cases/<mutation_id>/`: raw M6 artifacts for each mutation, including trace compare rows, counterexamples, certificate, rollback log, and validation stats.

`synthetic_mutation_replay` means the script tests M6 validator behavior on synthetic semantic-divergence traces; it does not execute Home Assistant integrations or real devices.
