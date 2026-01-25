from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ResourceLocator:
    """Resolve engine-related resource paths from a single root."""

    engine_root: Path

    @classmethod
    def from_env(cls, env_var: str = "ENGINE_ROOT", default_root: Optional[Path] = None) -> "ResourceLocator":
        """Create a locator using an optional environment override."""
        if default_root is None:
            default_root = Path.cwd()
        engine_root = Path(default_root)
        # Use os.environ directly to avoid optional imports in module scope.
        import os

        env_value = os.environ.get(env_var)
        if env_value:
            engine_root = Path(env_value)
        return cls(engine_root=engine_root.resolve())

    def resolve(self, relative_path: str | Path) -> Path:
        """Resolve a relative resource path from the engine root."""
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate
        return (self.engine_root / candidate).resolve()

    def schema_path(self) -> Path:
        return self.resolve("schemas/engine_output.schema.json")

    def output_path(self, output_relative_path: str | Path) -> Path:
        return self.resolve(output_relative_path)
