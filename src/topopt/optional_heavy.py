import os

if os.environ.get("TOPOPT_BUILD_MODE", "ON").upper() == "OFF":
    raise ImportError("Heavy optional dependency blocked in build_off mode.")

# Placeholder for heavy dependencies.
