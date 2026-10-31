import tempfile
import unittest
from pathlib import Path

from sports_vision.result_bundle import collect_results


class ResultBundleTests(unittest.TestCase):
    def test_downloads_survive_working_directory_cleanup(self):
        summary = {
            "outputs": {
                "annotated_video": "annotated.webm",
                "reports": ["heat.png"],
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ["annotated.webm", "tracking.csv", "heat.png"]:
                (root / name).write_bytes(name.encode())
            result = collect_results(root, summary)

        summary["outputs"]["reports"].clear()
        self.assertEqual(result["video"], b"annotated.webm")
        self.assertEqual(result["video_filename"], "annotated.webm")
        self.assertEqual(result["video_mime_type"], "video/webm")
        self.assertEqual(result["csv"], b"tracking.csv")
        self.assertEqual(result["reports"], [("heat.png", b"heat.png")])
        self.assertEqual(result["summary"]["outputs"]["reports"], ["heat.png"])
        self.assertEqual(result["size_bytes"], 34)

    def test_report_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "escapes"):
                collect_results(
                    Path(folder),
                    {"outputs": {"annotated_video": "annotated.webm", "reports": ["../private.png"]}},
                )

    def test_video_filename_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "simple output filename"):
                collect_results(
                    Path(folder),
                    {"outputs": {"annotated_video": "../private.webm", "reports": []}},
                )

    def test_rejects_unsupported_video_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "annotated.avi").write_bytes(b"video")
            (root / "tracking.csv").write_bytes(b"csv")
            with self.assertRaisesRegex(ValueError, "supported"):
                collect_results(
                    root,
                    {"outputs": {"annotated_video": "annotated.avi", "reports": []}},
                )

    def test_rejects_bundle_that_exceeds_session_memory_budget(self):
        summary = {
            "outputs": {
                "annotated_video": "annotated.webm",
                "reports": ["heat.png"],
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "annotated.webm").write_bytes(b"video")
            (root / "tracking.csv").write_bytes(b"csv")
            (root / "heat.png").write_bytes(b"image")

            with self.assertRaisesRegex(ValueError, "13 bytes.*12 bytes"):
                collect_results(root, summary, max_bytes=12)
