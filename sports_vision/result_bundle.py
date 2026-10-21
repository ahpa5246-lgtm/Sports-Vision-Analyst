"""Detach a completed result from its temporary working directory."""
from copy import deepcopy
from pathlib import Path

DEFAULT_RESULT_MEMORY_LIMIT_BYTES = 512 * 1024 * 1024


def _safe_output_file(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Result path escapes the analysis directory")
    return path


def collect_results(
    output: Path,
    summary: dict,
    *,
    max_bytes: int = DEFAULT_RESULT_MEMORY_LIMIT_BYTES,
) -> dict:
    if max_bytes < 1:
        raise ValueError("Result memory budget must be positive")

    root = output.resolve()
    video_path = _safe_output_file(root, "annotated.mp4")
    csv_path = _safe_output_file(root, "tracking.csv")
    report_paths = [
        (str(name), _safe_output_file(root, str(name)))
        for name in summary["outputs"]["reports"]
    ]
    paths = [video_path, csv_path, *(path for _, path in report_paths)]
    total_bytes = sum(path.stat().st_size for path in paths)
    if total_bytes > max_bytes:
        raise ValueError(
            f"Completed outputs use {total_bytes} bytes, exceeding the "
            f"{max_bytes} bytes session memory budget. Use a shorter clip."
        )

    reports = [(name, path.read_bytes()) for name, path in report_paths]
    return {
        "summary": deepcopy(summary),
        "video": video_path.read_bytes(),
        "csv": csv_path.read_bytes(),
        "reports": reports,
        "size_bytes": total_bytes,
    }
