import tempfile
import unittest
from pathlib import Path
from sports_vision.result_bundle import collect_results

class ResultBundleTests(unittest.TestCase):
    def test_downloads_survive_working_directory_cleanup(self):
        summary = {"outputs": {"reports": ["heat.png"]}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ["annotated.mp4", "tracking.csv", "heat.png"]:
                (root / name).write_bytes(name.encode())
            result = collect_results(root, summary)
        summary["outputs"]["reports"].clear()
        self.assertEqual(result["video"], b"annotated.mp4")
        self.assertEqual(result["csv"], b"tracking.csv")
        self.assertEqual(result["reports"], [("heat.png", b"heat.png")])
        self.assertEqual(result["summary"]["outputs"]["reports"], ["heat.png"])

    def test_report_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "escapes"):
                collect_results(Path(folder), {"outputs": {"reports": ["../private.png"]}})
