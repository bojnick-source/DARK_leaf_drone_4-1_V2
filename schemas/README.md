# v2 Schemas

This directory will host structured definitions for fragment inputs, outputs, and artifacts. Schemas ensure deterministic execution and unambiguous failure labeling.

Planned usage:
- Define JSON/YAML schemas for fragment configuration, metrics, and run manifests.
- Keep compatibility between the `v2_engine` truth layer and the `v2_studio` desktop workflows.
- Validate results before persistence or exchange with external tools.

## Available Schemas
- `run_output.schema.json`: Defines per-run output payloads (run_id, ok flag, optional fail label, inputs, metrics, artifact references).
