# Real-Inference Evidence Artifact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retain and validate the existing real-inference smoke metrics as a commit-bound JSON workflow artifact.

**Architecture:** Keep evidence construction in the existing integration test. Add a small file writer in that test module, narrow the environment skip to the model test, and let a normal unit test verify exact JSON persistence without loading YOLO. CI supplies the output path, validates the resulting JSON contract, and uploads only that file.

**Tech Stack:** Python 3.11, Pytest, GitHub Actions, JSON

**Spec:** `docs/superpowers/specs/2026-10-25-real-inference-evidence-artifact-design.md`

## Global Constraints

- Continue PR #2 branch `codex/persistent-analysis-workspace`; create no branch or PR.
- No product, model, tracker, calibration, UI, dependency, deployment, merge, or paid-service change.
- Retain the existing eight-frame 320×192 CPU smoke and stdout evidence line.
- Artifact validation must reject missing, malformed, incomplete, or non-positive memory/bundle evidence.
- Keep PR #2 draft and record exact RED/GREEN evidence and remaining limitations.

## Review Focus

- Normal suite without `RUN_REAL_INFERENCE=1`: writer test runs; model smoke skips.
- Missing parent directory: writer creates it before writing.
- Missing or malformed artifact: CI validation fails before upload can be treated as success.
- Incomplete keys or non-positive `peak_rss_bytes` / `bundle_size_bytes`: validation fails.
- Smoke failure before evidence creation: `if: always()` upload fails explicitly because the evidence file is required.

---

### Task 1: Persist and upload real-inference evidence

**Files:**
- Modify: `tests/test_real_inference.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/DEVELOPMENT_REVIEW.md`

**Interfaces:**
- Consumes: `REAL_INFERENCE_EVIDENCE_PATH` as an optional filesystem path.
- Produces: `artifacts/real-inference-evidence.json` containing exactly `model`, `tracker`, `device`, `frames_processed`, `download_names`, `bundle_size_bytes`, and `peak_rss_bytes`.

- [ ] **Step 1: Write the failing writer test**

Move the real-smoke skip condition onto the integration test, then add `test_writes_inspectable_evidence_json`. It calls `_write_evidence(path, evidence)` and asserts the created JSON round-trips exactly and creates its parent directory.

- [ ] **Step 2: Run CI to verify RED**

Run through the existing PR workflow.

Expected: the normal test job fails only with `NameError: _write_evidence is not defined`; the unchanged integration smoke remains independently green.

- [ ] **Step 3: Implement minimal JSON persistence**

Add `_write_evidence(path: Path, evidence: dict) -> None`, create the parent directory, and write UTF-8 sorted/indented JSON. In the integration smoke, call it when `REAL_INFERENCE_EVIDENCE_PATH` is present, while retaining the stdout line.

- [ ] **Step 4: Configure artifact validation and upload**

Set `REAL_INFERENCE_EVIDENCE_PATH=artifacts/real-inference-evidence.json` on the real-inference job. After Pytest, load the file with Python and assert the exact key set, eight frames, nonempty downloads, and positive bundle/RSS values. Upload it as `real-inference-evidence-${{ github.sha }}` with `if: always()` and `if-no-files-found: error`.

- [ ] **Step 5: Verify GREEN**

Expected: normal Pytest suite and compile check pass; real-inference smoke passes; JSON validation passes; the named artifact exists and its bytes match the recorded digest.

- [ ] **Step 6: Record evidence and preserve draft state**

Update `docs/DEVELOPMENT_REVIEW.md` and PR #2 with RED/GREEN run IDs, artifact ID/name/size/digest, the observed peak RSS, limits, and rollback. Verify the current head CI and leave the PR draft and unmerged.
