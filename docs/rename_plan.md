# Rename Plan (Phase 0 – planning only)

No renames executed yet. Planned batches will use `git mv`, update all references, and rerun CI in both modes.

| Current path | Proposed new path | Reason (main vs sub) | Reference updates needed | Risk | Verification steps |
| --- | --- | --- | --- | --- | --- |
| 4-1-drone-main/cpp/cli/main.cpp | 4-1-drone-main/cpp/cli/MAIN.cpp | MAIN (lift_cli entry point) → ALL CAPS | Update root `4-1-drone-main/CMakeLists.txt` target `lift_cli` to reference `MAIN.cpp`; adjust any docs/refs that mention the path | Medium | Follow Verification steps 1–3 below |
| 4-1-drone-main/cpp/cli/closeout_demo.cpp | 4-1-drone-main/cpp/cli/CLOSEOUT_DEMO.cpp | MAIN (CLI entry point) → ALL CAPS | Update root `4-1-drone-main/CMakeLists.txt` source list entry for target `closeout_demo` to point to the new filename; adjust any docs/refs that mention the path | Medium | Follow Verification steps 1–3 below |

Notes:
- Sub-files already conform to `lower_snake_case`; no additional renames planned unless new main entry points are added.
- Case-only renames will use two-step moves if needed for case-insensitive filesystems.
- Do-not-rename (mandated): `CMakeLists.txt`, workflow/config manifests (none present), `README.md`, directories `legacy/` or `archive/` (none present) remain reference-only.

## Verification steps (apply to each rename batch)
1) `cmake -S . -B build && cmake --build build`  
2) `ctest --test-dir build`  
3) If a feature flag matrix exists, rerun steps 1–2 for each flag value (e.g., OFF/ON).
