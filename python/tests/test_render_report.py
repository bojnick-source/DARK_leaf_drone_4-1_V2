import tempfile
import unittest
from pathlib import Path

from engine_ui.schema_validation import validate_payload_file
from tools.render_daily_dashboard import render_report


class RenderReportTests(unittest.TestCase):
    def test_report_contains_sentinels(self):
        repo_root = Path(__file__).resolve().parents[2]
        schema_path = repo_root / "schemas" / "engine_output.schema.json"
        payload_path = repo_root / "python" / "tests" / "fixtures" / "valid_engine_output.json"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            render_report(payload_path, schema_path, output_path)
            contents = output_path.read_text(encoding="utf-8")

        self.assertIn("Daily Dashboard Report", contents)
        self.assertIn("Validation: PASS", contents)
        result = validate_payload_file(payload_path, schema_path)
        self.assertTrue(result.is_valid)


if __name__ == "__main__":
    unittest.main()
