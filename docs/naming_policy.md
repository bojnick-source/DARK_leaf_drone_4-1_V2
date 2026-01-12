# Naming Policy

Goal: unify file naming with deterministic, history-preserving changes and zero behavioral differences.

## Definitions
- **Executable main files** (ALL CAPS base name): contain a program/CLI entry point (`main`) or are the top-level driver that wires multiple modules for a full run/demo. Files that mix an entry point with significant implementation (including test harnesses with `main()`) are still treated as executable mains and should follow ALL_CAPS; prefer factoring shared logic into sub-files. Example: `4-1-drone-main/cpp/cli/closeout_demo.cpp` (planned rename to `CLOSEOUT_DEMO.cpp`).
- **Contract docs**: repo-level canonical documentation/specs. These keep their mandated names (e.g., `README.md`) and are already uppercase-compliant.
- **Sub files** (module internals): implementation or header units that do not host entry points—helpers, models, algorithms, and supporting utilities within `cpp/engine/**` and similar module trees.

## Rules
1. **Executable main files** use `ALL_CAPS.ext` (keep extension). Examples: CLI entry points, top-level harnesses.  
2. **Sub files** use `lower_snake_case.ext` (chosen style).  
   Rationale: current modules already use snake_case across `cpp/engine/**` and `cpp/cli/**`, so staying with snake_case avoids churn and keeps consistency.  
3. **Directories** stay as-is unless a high-safety justification is documented; no legacy wiring added.  
4. **History preservation**: use `git mv` (case-only changes may need a two-step rename for case-insensitive filesystems, e.g., `git mv file.cpp file_tmp.cpp && git mv file_tmp.cpp FILE.cpp`).  
5. **Reference completeness**: update all includes/imports/CMake paths/scripts/docs when a file is renamed.  
6. **Determinism**: no functional changes in rename batches; CI/tests must remain green.

## Exceptions (do not rename)
- Tool-mandated names: `CMakeLists.txt`, anything under `.github/`, workflow filenames, package/config manifests that tooling expects, `README.md` (already uppercase and mandated).
- Legacy/reference artifacts remain untouched unless explicitly approved.
