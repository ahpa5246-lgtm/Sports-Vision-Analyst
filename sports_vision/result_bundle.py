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
    video_name = summary["outputs"].get("annotated_video")
    if (
        not isinstance(video_name, str)
        or not video_name
        or "/" in video_name
        or "\\" in video_name
    ):
        raise ValueError("Annotated video filename must be a simple output filename")
    video_path = _safe_output_file(root, video_name)
    video_mime_type = {
        ".webm": "video/webm",
        ".mp4": "video/mp4",
    }.get(video_path.suffix.lower())
    if video_mime_type is None:
        raise ValueError("Annotated video must use a supported .webm or .mp4 extension")
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
        "video_filename": video_path.name,
        "video_mime_type": video_mime_type,
        "csv": csv_path.read_bytes(),
        "reports": reports,
        "size_bytes": total_bytes,
    }
