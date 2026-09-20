# FloWeaver

This repository contains the code for the paper **FloWeaver: Validation-guided Synthesis of Low-Latency Execution Flows for Cross-Device IoT Automation**.

FloWeaver analyzes and schedules Home Assistant routines across BLE, cloud, and local integrations. It builds evidence-backed constraint profiles, extracts action semantics, generates execution plans and custom components, and evaluates plans through differential replay and counterexample analysis.

## Setup

Requires Python 3.10 or later. Run commands from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest
```

## Usage

Build a constraint profile from documentation, integration source, and test snapshots:

```bash
python floweaver_cli.py build-profile \
  --docs-root data/docs_snapshot \
  --repo-root data/repo_snapshot \
  --tests-root data/tests_snapshot \
  --out-dir data/profiles/default
```

Describe the routine in a VDev specification, map its actions to source files in a Source specification, and configure observation and replay in a Run specification. The JSON files in `data/specs/` illustrate these formats; source paths and service mappings should match your integrations.

```bash
python floweaver_cli.py optimize \
  --integration-name my_routine \
  --profile-path data/profiles/default/ha_profile.json \
  --vdev-spec path/to/vdev.json \
  --source-spec path/to/sources.json \
  --run-spec path/to/run.json \
  --out-dir outputs/my_routine
```

Results include the execution plan, dependency graph, replay comparisons, counterexamples, execution certificate, and a Home Assistant component under `reassembly/`. Follow the generated `install.md` to install the component.

Use `python floweaver_cli.py --help` for all commands.

## Configuration

Optional model-backed candidate discovery uses these environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `FLOWEAVER_LLM_API_BASE_URL` | Chat-completions endpoint URL | Unset |
| `FLOWEAVER_LLM_API_KEY` | Endpoint access token | Unset |
| `FLOWEAVER_LLM_MODEL` | Model identifier | `gpt-5` |
| `FLOWEAVER_LLM_TIMEOUT_S` | Request timeout in seconds | 120 for profile discovery; 300 for detector generation |
| `FLOWEAVER_LLM_MAX_ATTEMPTS` | Detector request attempts; 0 means no fixed limit | `0` |
| `FLOWEAVER_LLM_RETRY_BACKOFF_S` | Detector retry delay in seconds | `0.75` |

Copy `.env.example` to `.env`, fill in local values, and load them before running:

```bash
set -a
source .env
set +a
```

Add `--enable-llm-discovery` to `build-profile` to enable candidate discovery. The optimizer can use the configured endpoint when critical actions need additional grounding. Keep credentials in the environment, outside committed specifications. `${FLOWEAVER_LLM_API_BASE_URL}` in archived reports is a redacted endpoint reference. Repository paths in published artifacts are relative to the repository root.

## Project Layout

- `profile_builder/`: evidence extraction, rule normalization, validation, and profiles.
- `optimizer/`: interpretation, semantic extraction, scheduling, component generation, and validation.
- `alignment_layer/` and `counterexample_layer/`: semantic alignment and counterexample analysis.
- `runtime/` and `dsl/`: replay, observations, and data contracts.
- `tests/`, `scripts/`, and `data/`: regression tests, evaluation tools, and input snapshots.

## Tests

```bash
python -m pytest
```
