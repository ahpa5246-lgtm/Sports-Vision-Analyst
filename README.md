# Sports Vision Analyst

A working single-camera football analytics pipeline. It detects and tracks players and the ball, maps image positions to real pitch coordinates with homography, estimates player speed and distance, classifies the two teams by jersey color, estimates possession and common formations, optionally exports pose keypoints, and renders a tactical mini-map over the source video.

## What it produces

For every analyzed match the pipeline writes:

- `annotated.mp4` — tracked players, IDs, team, speed and tactical mini-map.
- `tracking.csv` — frame/time/track/team/metric x-y/speed/distance/confidence/bounding box.
- `summary.json` — team distance, possession estimate, player totals/top speed and dominant formation.
- `team_1_heatmap.png`, `team_2_heatmap.png` — spatial occupancy heatmaps when team samples exist.
- `poses.jsonl` — optional 17-keypoint pose observations associated with track IDs.

## Architecture

```text
video
  -> Ultralytics detector (person + sports ball)
  -> multi-object tracker (ByteTrack by default)
  -> jersey-color team clustering
  -> foot point extraction
  -> calibrated homography: pixels -> pitch meters
  -> temporal analytics: speed + distance + possession
  -> formation estimator
  -> optional pose model + track association
  -> annotated video + CSV + JSON + heatmaps
```

The default model names follow the current Ultralytics model family (`yolo26n.pt` and `yolo26n-pose.pt`). Both are CLI options, so you can use another official model or custom football weights without changing code.

## 1. Install

Python 3.10+ is supported. A CUDA-capable PyTorch install is recommended for long matches.

```bash
git clone https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst.git
cd Sports-Vision-Analyst
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[full]"
```

Ultralytics downloads official model weights automatically the first time a model is used.

## 2. Calibrate the camera

Metric analytics require mapping image landmarks to known pitch coordinates. For a fixed camera, do this once per camera setup.

If all four pitch corners are visible:

```bash
sports-vision-calibrate match.mp4 --output calibration.json
```

Click the corners in this default field-coordinate order:

```text
(0,0) -> (105,0) -> (105,68) -> (0,68)
```

If the full pitch is not visible, use any four or more visible pitch landmarks whose metric coordinates you know. Supply their coordinates in the same order you will click them:

```bash
sports-vision-calibrate match.mp4 \
  --field-points "0,13.84;16.5,13.84;16.5,54.16;0,54.16" \
  --output calibration.json
```

The important rule is correspondence: click image landmark `i` for field coordinate `i`.

## 3. Analyze a match

```bash
sports-vision match.mp4 \
  --calibration calibration.json \
  --output runs/match-01 \
  --device 0
```

Enable pose export:

```bash
sports-vision match.mp4 --calibration calibration.json --output runs/match-01 --device 0 --pose
```

CPU mode works but is substantially slower:

```bash
sports-vision match.mp4 --calibration calibration.json --device cpu
```

Useful knobs:

```text
--model yolo26n.pt          detector or your custom football weights
--tracker bytetrack.yaml    can also use botsort.yaml
--imgsz 1280                larger helps small-ball detection but costs GPU time
--conf 0.25                 detector confidence
--person-class 0            class ID for person in your model
--ball-class 32             COCO sports-ball class; change for custom models
--pose                      write pose keypoints
--pose-stride 5             pose every N frames
```

## 4. Streamlit UI

```bash
streamlit run app.py
```

Upload the video and calibration JSON, choose model/tracker/device, run the pipeline, preview the annotated result, and download the generated files.

## Docker

```bash
docker build -t sports-vision-analyst .
docker run --rm -p 8501:8501 sports-vision-analyst
```

For NVIDIA GPU use, run with the NVIDIA Container Toolkit and a CUDA-compatible PyTorch base/runtime if you want GPU acceleration inside Docker.

## Accuracy notes

This repository is an end-to-end executable baseline, not a claim that generic COCO weights are optimal for professional match analysis.

1. The default detector can miss a tiny or motion-blurred ball. Replacing `--model` with football-specific weights is the biggest accuracy upgrade.
2. Metric speed/distance are only as good as camera calibration. A fixed tactical camera is ideal.
3. A static homography assumes a fixed camera. Broadcast footage with active pan/tilt/zoom needs dynamic pitch-keypoint calibration per frame or per camera segment.
4. Jersey clustering treats the two largest color clusters as the teams and rejects distant outliers; referees and goalkeepers may remain `team=0`.
5. Formation output is intentionally conservative: it records a formation only when at least nine team players are visible and matches spatial lines to common formations.
6. Ball possession is a proximity estimate, not an official event-data definition.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

The unit tests cover metric homography, speed/distance accumulation with impossible-jump rejection, and formation estimation.

## Project layout

```text
sports_vision/
  analytics.py        metric tracking, possession, formations
  calibrate.py        interactive homography calibration
  cli.py              command-line entry point
  config.py           runtime settings
  homography.py       pixel-to-meter transformation
  pipeline.py         end-to-end inference loop
  report.py           heatmaps
  team_classifier.py  online jersey clustering
  visualize.py        annotations and tactical mini-map
app.py                 Streamlit UI
```
