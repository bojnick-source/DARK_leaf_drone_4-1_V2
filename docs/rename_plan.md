# Rename Plan (Phase 0 – planning only)

No renames executed yet. Planned batches will use `git mv`, update all references, and rerun CI in both modes.

No renames planned. Legacy vendor sources have been removed.

Notes:
- Sub-files already conform to `lower_snake_case`; no additional renames planned unless new main entry points are added.
- Case-only renames will use two-step moves if needed for case-insensitive filesystems.
- Do-not-rename (mandated): `CMakeLists.txt`, workflow/config manifests (none present), `README.md`, directories `legacy/` or `archive/` (none present) remain reference-only.

## Verification steps (apply to each rename batch)
1) `cmake -S . -B build && cmake --build build`  
2) `ctest --test-dir build`  
3) If a feature flag matrix exists, rerun steps 1–2 for each flag value (e.g., OFF/ON).
