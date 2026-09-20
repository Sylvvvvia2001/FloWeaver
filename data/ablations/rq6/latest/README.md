# RQ6 Ablation Study

Generated: 2026-07-07T10:06:37.814869+00:00
Input workbook: `data/external/ifttt_samples_vibeaura_simulated_estimates.xlsx`
NaiveTopo source: `data/baselines/naive_topo_parallel/realistic_simulation/naive_topo_realistic_rows.csv`

Variants:
- `without_rollback`: full latency model, but cases requiring rollback are counted as validation failures.
- `without_micro`: uses full FloWeaver macro/coarse latency and keeps validator/rollback pass status.
- `action_only`: action-level ablation estimated from NaiveTopo action scheduling plus FloWeaver-style rollback recovery.
- `full_floweaver`: copied from current system estimate sheet for reference.

Main dataset summary:
- long-chain / action_only: pass=61.54%, latency=13.2986s, gain=25.09%, mean_rb=1.4231, runtime=30.2014s
- long-chain / full_floweaver: pass=96.15%, latency=4.9203s, gain=74.85%, mean_rb=1.8846, runtime=37.7754s
- long-chain / without_micro: pass=80.77%, latency=5.7223s, gain=71.4%, mean_rb=2, runtime=34.3756s
- long-chain / without_rollback: pass=7.69%, latency=2.533s, gain=73.9%, mean_rb=2.7692, runtime=27.405s
- smart-home / action_only: pass=80.0%, latency=3.2033s, gain=25.78%, mean_rb=0.8, runtime=10.8066s
- smart-home / full_floweaver: pass=98.0%, latency=1.9434s, gain=51.65%, mean_rb=1.2, runtime=13.6668s
- smart-home / without_micro: pass=90.0%, latency=2.1392s, gain=46.72%, mean_rb=1.28, runtime=12.4368s
- smart-home / without_rollback: pass=38.0%, latency=1.6129s, gain=30.83%, mean_rb=1.86, runtime=10.2383s
