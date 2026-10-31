from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def _wait_for_streamlit(process: subprocess.Popen, log_path: Path) -> None:
    health_url = "http://127.0.0.1:8501/_stcore/health"
    for _ in range(90):
        if process.poll() is not None:
            detail = log_path.read_text(encoding="utf-8", errors="replace")[-5000:]
            raise RuntimeError(f"Streamlit exited before becoming healthy:\n{detail}")
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    detail = log_path.read_text(encoding="utf-8", errors="replace")[-5000:]
    raise TimeoutError(f"Streamlit did not become healthy within 90 seconds:\n{detail}")


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_STREAMLIT_UI") != "1",
    reason="set RUN_STREAMLIT_UI=1 for the real-footage browser acceptance",
)
def test_streamlit_real_football_upload_results_downloads_and_reruns(tmp_path: Path):
    from playwright.sync_api import expect, sync_playwright

    repo_root = Path(__file__).resolve().parents[1]
    video_path = Path(os.environ["REAL_FOOTBALL_CLIP"])
    calibration_path = Path(os.environ["REAL_FOOTBALL_CALIBRATION"])
    evidence_dir = Path(os.environ.get("UI_EVIDENCE_DIR", "artifacts/ui"))
    evidence_dir.mkdir(parents=True, exist_ok=True)

    assert video_path.is_file(), "the prepared real-football MP4 must exist"
    assert calibration_path.is_file(), "the matching camera calibration fixture must exist"
    attribution_path = evidence_dir / "attribution.json"
    attribution = json.loads(attribution_path.read_text(encoding="utf-8"))

    log_path = evidence_dir / "streamlit.log"
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

    with log_path.open("w", encoding="utf-8") as server_log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless=true",
                "--server.address=127.0.0.1",
                "--server.port=8501",
                "--browser.gatherUsageStats=false",
            ],
            cwd=repo_root,
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_streamlit(process, log_path)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                try:
                    page = browser.new_page(
                        viewport={"width": 1440, "height": 1000},
                        accept_downloads=True,
                    )
                    page.set_default_timeout(60_000)
                    page.set_default_navigation_timeout(60_000)
                    page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Sports Vision Analyst")).to_be_visible()

                    upload_inputs = page.locator('input[type="file"]')
                    expect(upload_inputs).to_have_count(2)
                    upload_inputs.nth(0).set_input_files(str(video_path))
                    upload_inputs.nth(1).set_input_files(str(calibration_path))
                    expect(page.get_by_role("button", name="Analyze match")).to_be_enabled()
                    page.screenshot(
                        path=str(evidence_dir / "analyze-uploaded.png"),
                        full_page=True,
                    )

                    page.get_by_role("button", name="Analyze match").click()
                    expect(
                        page.get_by_text(
                            "Open Results to review the match and download reports.",
                            exact=True,
                        )
                    ).to_be_visible(timeout=600_000)
                    page.screenshot(
                        path=str(evidence_dir / "analyze-complete.png"),
                        full_page=True,
                    )

                    page.get_by_text("Results", exact=True).click()
                    expect(page.get_by_text("Match results", exact=True)).to_be_visible()
                    video_player = page.locator("video")
                    expect(video_player).to_have_count(1)
                    preview = video_player.first.evaluate(
                        "(element) => ({src: element.currentSrc || element.src, readyState: element.readyState, duration: Number.isFinite(element.duration) ? element.duration : null})"
                    )
                    video_player.first.evaluate("(element) => { element.muted = true; return element.play(); }")
                    page.wait_for_function(
                        """() => {
                          const element = document.querySelector("video");
                          return element && element.readyState >= 2 && element.currentTime > 0;
                        }""",
                        timeout=15_000,
                    )
                    playback = video_player.first.evaluate(
                        """(element) => {
                          const result = {
                            played: element.currentTime > 0,
                            currentTime: element.currentTime,
                            readyState: element.readyState,
                            error: element.error ? element.error.message : null
                          };
                          element.pause();
                          return result;
                        }"""
                    )
                    assert playback["played"], f"Annotated video preview did not play: {playback}"
                    assert playback["readyState"] >= 2, f"Annotated video was not ready: {playback}"
                    page.screenshot(
                        path=str(evidence_dir / "results-desktop.png"),
                        full_page=True,
                    )

                    page.get_by_text("Calibration guide", exact=True).click()
                    expect(
                        page.get_by_text("Map the pitch before measuring movement", exact=True)
                    ).to_be_visible()
                    page.get_by_text("Results", exact=True).click()
                    expect(page.get_by_role("heading", name="Match results")).to_be_visible()
                    expect(page.locator("video")).to_have_count(1)

                    page.set_viewport_size({"width": 768, "height": 900})
                    page.wait_for_timeout(500)
                    narrow_overflow = page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth"
                    )
                    page.screenshot(
                        path=str(evidence_dir / "results-narrow.png"),
                        full_page=True,
                    )

                    def save_download(label: str, filename: str) -> Path:
                        target = tmp_path / filename
                        with page.expect_download(timeout=60_000) as download_info:
                            page.get_by_text(label, exact=True).click()
                        download_info.value.save_as(str(target))
                        assert target.is_file() and target.stat().st_size > 0
                        return target

                    tracking_path = save_download("Download tracking CSV", "tracking.csv")
                    summary_path = save_download("Download summary JSON", "summary.json")
                    annotated_path = save_download("Download annotated video", "annotated.webm")

                    csv_lines = tracking_path.read_text(encoding="utf-8").splitlines()
                    assert csv_lines and csv_lines[0].startswith("frame,time_s,")
                    assert len(csv_lines) > 1, "the real football clip produced no tracked-player rows"
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    assert summary["frames_processed"] > 0

                    page.get_by_role("button", name="Clear results").click()
                    expect(
                        page.get_by_text(
                            "No completed analysis yet. Open Analyze to upload a match and calibration.",
                            exact=True,
                        )
                    ).to_be_visible()
                    page.screenshot(
                        path=str(evidence_dir / "results-cleared.png"),
                        full_page=True,
                    )

                    evidence = {
                        "status": "passed",
                        "source": attribution,
                        "frames_processed": summary["frames_processed"],
                        "tracking_rows": len(csv_lines) - 1,
                        "download_sizes_bytes": {
                            "tracking.csv": tracking_path.stat().st_size,
                            "summary.json": summary_path.stat().st_size,
                            "annotated.webm": annotated_path.stat().st_size,
                        },
                        "video_preview": preview,
                        "video_playback": playback,
                        "rerun_preserved_result": True,
                        "narrow_horizontal_overflow": bool(narrow_overflow),
                        "viewports": ["1440x1000", "768x900"],
                        "screenshots": [
                            "analyze-uploaded.png",
                            "analyze-complete.png",
                            "results-desktop.png",
                            "results-narrow.png",
                            "results-cleared.png",
                        ],
                    }
                    (evidence_dir / "results.json").write_text(
                        json.dumps(evidence, indent=2) + "\n",
                        encoding="utf-8",
                    )
                finally:
                    browser.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
