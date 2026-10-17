"""Detach a completed result from its temporary working directory."""
from copy import deepcopy
from pathlib import Path


def collect_results(output: Path, summary: dict) -> dict:
    root = output.resolve()
    reports = []
    for name in summary["outputs"]["reports"]:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Report path escapes the analysis directory")
        reports.append((str(name), path.read_bytes()))
    return {"summary": deepcopy(summary), "video": (root / "annotated.mp4").read_bytes(),
            "csv": (root / "tracking.csv").read_bytes(), "reports": reports}
