# Sports Vision Analyst: engineering review, 2026-10-18

## Scope and intent
Owner requested continued implementation and severe comparison with released products. This remains a bounded repair milestone, not a full completion claim. Local/offline architecture is retained; no new paid service or deployment.

Core journey: Upload → calibration → analysis → results/downloads.

## Decision and implementation
Separate Analyze, Results, Calibration guide. Keep completed output bytes in Streamlit session state after temporary cleanup, publish only complete bundles and preserve earlier results on analysis failure. Uploaded video names no longer control local paths.

The follow-up memory-safety stage now measures every completed output before any result bytes are copied. Bundles over 512 MiB are rejected with a request to use a shorter clip, the previous successful result remains available, and the Results workspace shows the retained bundle size. This converts the documented unbounded-memory risk into a deterministic guard; it does not make session storage persistent.

Alternative: decorate the existing home page while leaving workflows and state bugs unchanged. Rejected because appearance cannot repair lost results or crowded controls. Existing architecture remains intact.

## Reference research
Official feature/product pages consulted for task hierarchy and separation of primary work from setup/reference. No source, artwork, icon or layout copied:
https://www.hudl.com/products/sportscode
https://kinovea.org/
https://www.hudl.com/

Web-text inspection is not a visual screenshot comparison. These sources are a starting shortlist, not completed visual evidence. Do not mark the comparative design gate passed. A missing or inaccessible visual reference remains an open item.

## Evidence and harsh self-review
Three result-bundle unittest cases pass locally: results survive deleted working-directory cleanup, report traversal is rejected, and an oversized bundle is rejected before copying. `python -m compileall sports_vision tests` passes for the changed module and tests. GitHub Actions run 39089719464 installed the project from `.[dev]`, passed the full six-test Pytest suite, and compiled `sports_vision` plus `app.py` on commit `e23d48d`. The run also reported GitHub's Node 20 action-runtime deprecation warning for `actions/checkout@v4` and `actions/setup-python@v5`; this is a maintenance item rather than a product-test failure.

A bounded real-model integration job now generates an eight-frame 320×192 MP4, uses a valid full-frame calibration, loads `yolo26n.pt`, runs ByteTrack on CPU, and detaches the annotated video, tracking CSV and summary JSON from the deleted temporary directory. It validates every exposed download as non-empty and keeps the detached bundle below the 512 MiB output ceiling. GitHub Actions run 39592316974 passed both the normal test job and `real-inference-smoke` on commit `338f03b`; the smoke step completed in seven seconds after dependency installation.

The follow-up evidence-artifact milestone made those exact metrics inspectable without changing product behavior. Test-only run 40183872114 failed the normal job only at `_write_evidence(evidence_path, evidence)` with `NameError: name '_write_evidence' is not defined` while the unchanged real-inference job remained green. Writer implementation run 40187881249 then passed the normal suite (`7 passed, 1 skipped`), compile check, and real smoke (`1 passed, 1 deselected`).

Workflow run 40190002085 completed both jobs successfully after the CI contract was added on branch-head commit `d3e6fab3c86c7881e27b02584a47f515111d50f7`: the normal job reported `7 passed, 1 skipped` and compiled `sports_vision` plus `app.py`; the real-inference job passed the smoke, validated the exact JSON key set and positive values, and uploaded artifact `real-inference-evidence-b7a55487e785c5dd33faf6e975a0c8f3faaa374f` (ID 12597434678, 345 bytes, SHA-256 `10d007d10060b4b18d7d2784483caecb8b5a64d8450c9931dd06d1484db567b7`). A fresh download produced the same archive digest and one 251-byte `real-inference-evidence.json` file. Its evidence is: model `yolo26n.pt`; tracker `bytetrack.yaml`; device `cpu`; 8 processed frames; downloads `annotated.mp4`, `summary.json`, `tracking.csv`; bundle size 10,584 bytes; peak RSS 852,156,416 bytes. Because pull-request workflows test GitHub's synthetic merge ref, the artifact name carries merge-test SHA `b7a5548`; workflow metadata separately records head branch `codex/persistent-analysis-workspace` and head SHA `d3e6fab`.

Full-length football footage and Streamlit interaction have not run. The synthetic clip proves model loading, tracker execution, output encoding, post-cleanup download bytes, and retained evidence; it does not prove player/ball accuracy or professional-match throughput. The 512 MiB limit remains an output-bundle guard, not a measured hosting recommendation; the recorded 852,156,416-byte peak is specific to this runner process and includes model/media overhead. Persistence still ends with the browser session.

The Senior Skills example visual gate was run and correctly returned BLOCKED_UNVERIFIED_DESIGN; its draft lacks verified asset licenses. That result is framework evidence, not a project-specific visual pass. Actual screenshots, app-commit binding, keyboard/RTL checks, and task observations are required before release readiness.

## Next acceptance boundary
Exercise the Streamlit upload → analysis → Results/download journey across reruns with a short real football clip. Capture actual app screenshots and task observations before comparative visual approval. Do not treat the synthetic smoke as accuracy evidence or approve public hosting from its RSS value.

Rollback: revert this milestone branch before merge. Do not merge or deploy automatically. Future runs must inspect open PRs and continue this branch before creating duplicate work.
