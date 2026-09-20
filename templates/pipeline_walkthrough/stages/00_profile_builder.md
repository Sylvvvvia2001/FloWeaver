# 00 Profile Builder

What you provide:
- HA docs snapshot: `../shared/docs_snapshot/`
- HA repo snapshot: `../shared/repo_snapshot/`

What the builder produces:
- `../shared/profile_builder_output/evidence_bank.json`
- `../shared/profile_builder_output/rules_soft.json`
- `../shared/profile_builder_output/gate_result.json`
- `../shared/profile_builder_output/hardening_decisions.json`
- `../shared/profile_builder_output/ha_profile.json`

Why it exists:
- converts docs/code evidence into a reusable HA-aware rule/profile file
