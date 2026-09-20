# Pipeline Walkthrough Templates

This folder is a teaching aid. It is not part of the runtime pipeline, is not imported by the optimizer, and is safe to delete.

Purpose:
- show what a first-time user needs to prepare
- show what each module roughly reads and writes
- give one concrete end-to-end snapshot without reading the full code first

Layout:
- `shared/`: example inputs and outputs copied or derived from the repo's demo artifacts
- `stages/`: one short note per stage explaining what the stage expects and what it produces

Notes:
- Most files under `shared/optimizer_outputs/` are real demo outputs copied from `data/optimizer_runs/vdev_demo_m7/`
- Files under `shared/m0_observation/` are small hand-written examples aligned with the current trace schema
- These files are documentation samples, not golden tests and not source code modules
