# v2 Python Modules

This directory contains all Python code related to the v2 drone computational engineering system, consolidated from multiple previous locations.

## Structure

```
v2/python/
├── ai/                  # AI and knowledge modules
│   ├── engineering_ai.py   # Engineering knowledge engine with TF-IDF retrieval
│   ├── memory.py           # Memory store for context and history
│   └── __init__.py         # Exports: EngineeringKnowledgeBase, EngineeringQueryEngine, etc.
├── engine/              # C++ engine bridge
│   ├── v2_engine.py        # Python interface to v2_engine_cli binary
│   ├── v2_run_manifest.py  # Run manifest handling and serialization
│   └── __init__.py         # Exports: find_engine_cli, run_engine, run_id_from_seed, etc.
├── tools/               # Utilities and helper scripts
│   ├── parse_results.py    # Parse v2 engine JSON outputs
│   ├── run_batch.py        # Batch execution utilities
│   └── verify_compile_db_isolation.py  # Build verification
└── __init__.py          # Top-level exports
```

## Usage

### AI Knowledge Engine

```python
from v2.python.ai import EngineeringKnowledgeBase, EngineeringQueryEngine

# Load knowledge from docs/ai_knowledge/
kb = EngineeringKnowledgeBase.from_directory("docs/ai_knowledge")
engine = EngineeringQueryEngine(kb)

# Query the knowledge base
result = engine.query("What is the lift equation?")
print(result.answer)
```

### Engine Bridge

```python
from v2.python.engine import find_engine_cli, run_engine

# Find the v2 engine binary
engine = find_engine_cli()
if engine:
    # Run the engine
    result = run_engine(
        engine_cli=engine,
        canonical_input='{"scalars":{"mass":1.0}}',
        artifact_root="artifacts/"
    )
    print(result)
```

### Run Manifest

```python
from v2.python.engine import run_id_from_seed, format_scalar

# Generate deterministic run IDs
run_id = run_id_from_seed("my-experiment-001")
print(f"Run ID: {run_id}")

# Format numeric values for canonical representation
value = format_scalar(3.14159, precision=6)
print(f"Value: {value}")
```

## Integration with Legacy Code

The v2.python modules are integrated with the existing codebase:

- **reidce package**: Re-exports AI modules for backward compatibility
- **sfcs_mdp package**: Uses v2.python.engine for C++ engine integration
- **Tests**: All tests updated to use new import paths

## Migration Notes

This consolidation moved files from:
- `src/reidce/engineering_ai.py` → `v2/python/ai/engineering_ai.py`
- `src/sfcs_mdp/v2_engine.py` → `v2/python/engine/v2_engine.py`
- `src/sfcs_mdp/v2_run_manifest.py` → `v2/python/engine/v2_run_manifest.py`
- `python/tools/v2/*` → `v2/python/tools/*`

All imports have been updated accordingly, and backward compatibility is maintained through re-exports in the reidce package.
