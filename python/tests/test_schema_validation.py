import unittest
from pathlib import Path

from engine_ui.schema_validation import validate_payload_file


class SchemaValidationTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.schema_path = self.repo_root / "schemas" / "engine_output.schema.json"
        self.valid_payload = self.repo_root / "python" / "tests" / "fixtures" / "valid_engine_output.json"
        self.invalid_payload = self.repo_root / "python" / "tests" / "fixtures" / "invalid_engine_output.json"

    def test_valid_payload(self):
        result = validate_payload_file(self.valid_payload, self.schema_path)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])

    def test_invalid_payload(self):
        result = validate_payload_file(self.invalid_payload, self.schema_path)
        self.assertFalse(result.is_valid)
        self.assertIn("run_id", result.missing_fields)


if __name__ == "__main__":
    unittest.main()
