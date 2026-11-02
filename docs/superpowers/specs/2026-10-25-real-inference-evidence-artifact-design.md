# Real-Inference Evidence Artifact Design

**Date:** 2026-10-25  
**Status:** owner-authorized bounded milestone  
**PR:** #2 on `codex/persistent-analysis-workspace`

## Intent

Make the existing bounded `YOLO26n + ByteTrack` smoke evidence inspectable after the job ends. The current test prints valid JSON to stdout, but the value is not retained as a named workflow artifact.

## Goals

- Preserve exact model, tracker, device, processed-frame, download-name, bundle-size, and peak-RSS values in one JSON file.
- Validate the evidence schema and positive numeric values before upload.
- Bind the artifact to the workflow run and commit.
- Upload evidence even when the real-inference test fails after creating the file.

## Non-goals

- No model, tracker, calibration, inference, UI, hosting, or result-retention behavior changes.
- No accuracy, full-match performance, or production-memory claim.
- No new dependency, deployment, secret, or paid resource.

## Approaches considered

1. Keep stdout only. Rejected because log parsing is transient and awkward for later review.
2. Write to GitHub Job Summary. Rejected because it is presentation-only and not a machine-readable retained file contract.
3. Write and upload a JSON artifact. Selected because the existing test already owns the evidence values and GitHub Actions can retain the exact bytes without changing product code.

## Design

The integration test reads `REAL_INFERENCE_EVIDENCE_PATH`. When set, it creates the parent directory and writes the same sorted JSON object that it prints. A focused unit test exercises the evidence writer without loading the model. CI sets the path to `artifacts/real-inference-evidence.json`, validates that file after the smoke test, and uploads it with `if: always()` and `if-no-files-found: error`.

## Acceptance

- A test-only commit fails because the evidence-writer interface does not exist.
- The normal suite and compile check remain green.
- The real-inference job passes on CPU and writes valid JSON.
- The uploaded artifact contains the expected keys; `frames_processed == 8`; `bundle_size_bytes > 0`; `peak_rss_bytes > 0`.
- PR #2 remains draft and unmerged; review documentation records exact run, artifact ID, size, digest, limitations, and rollback.

## Risks and rollback

RSS is runner/process evidence, not a stable cross-machine benchmark. The artifact must not be interpreted as hosting guidance. Rollback is a revert of this milestone's commits; no data migration or external resource exists.
