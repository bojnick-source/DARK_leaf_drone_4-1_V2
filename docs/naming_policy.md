# Naming Policy

Goal: unify file naming with deterministic, history-preserving changes and zero behavioral differences.

## Definitions
- **Main files** (ALL CAPS base name): entrypoints, top-level orchestrators, or primary contract docs/CLIs.
- **Sub files** (module internals): implementations, helpers, and headers under modules.

## Rules
1. **Main files** use `ALL_CAPS.ext` (keep extension). Examples: CLI entrypoints, top-level harnesses.  
2. **Sub files** use `lower_snake_case.ext` (chosen style). Rationale: existing code already follows snake_case (e.g., `cpp/engine/core/cache_key.cpp`, `cpp/engine/analysis/closeout_eval.cpp`), so adopting snake_case avoids churn and aligns with current convention.  
3. **Directories** stay as-is unless a high-safety justification is documented; no legacy wiring added.  
4. **History preservation**: use `git mv` (case-only changes may need a two-step rename for case-insensitive filesystems).  
5. **Reference completeness**: update all includes/imports/CMake paths/scripts/docs when a file is renamed.  
6. **Determinism**: no functional changes in rename batches; CI/tests must remain green.

## Exceptions (do not rename)
- Tool-mandated names: `CMakeLists.txt`, anything under `.github/`, workflow filenames, package/config manifests that tooling expects, `README.md`.
- Legacy/reference artifacts remain untouched unless explicitly approved.

