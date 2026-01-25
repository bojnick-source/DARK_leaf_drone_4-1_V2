import os
import tempfile
import unittest
from pathlib import Path

from engine_ui.resource_locator import ResourceLocator


class ResourceLocatorTests(unittest.TestCase):
    def test_resolve_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            locator = ResourceLocator(engine_root=Path(tmpdir))
            resolved = locator.resolve("schemas/engine_output.schema.json")
            self.assertEqual(resolved, Path(tmpdir) / "schemas/engine_output.schema.json")

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["ENGINE_ROOT"] = tmpdir
            locator = ResourceLocator.from_env(default_root=Path("/fallback"))
            self.assertEqual(locator.engine_root, Path(tmpdir).resolve())
        os.environ.pop("ENGINE_ROOT", None)

    def test_schema_path(self):
        locator = ResourceLocator(engine_root=Path("/tmp"))
        self.assertEqual(locator.schema_path(), Path("/tmp/schemas/engine_output.schema.json"))


if __name__ == "__main__":
    unittest.main()
