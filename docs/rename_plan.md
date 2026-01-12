# Rename Plan (Phase 0 – planning only)

No renames executed yet. Planned batches will use `git mv`, update all references, and rerun CI in both modes.

| Current path | Proposed new path | Reason (main vs sub) | Reference updates needed | Risk | Verification steps |
| --- | --- | --- | --- | --- | --- |
| cpp/cli/closeout_demo.cpp | cpp/cli/CLOSEOUT_DEMO.cpp | Main CLI harness/entrypoint → must be ALL CAPS | `CMakeLists.txt` source list for target `closeout_demo`; any includes/docs pointing to the path | Medium (entrypoint path change) | `cmake -S . -B build && cmake --build build && ctest --test-dir build` (repeat for ON/OFF if matrixed) |

Notes:
- Sub-files already conform to `lower_snake_case`; no additional renames planned unless new main entrypoints are added.
- Case-only renames will use two-step moves if needed for case-insensitive filesystems.
