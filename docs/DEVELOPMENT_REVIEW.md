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

Full model inference and Streamlit interaction have not run. The 512 MiB limit is a safety ceiling, not a measured hosting recommendation; Streamlit and media decoding add overhead. Persistence still ends with the browser session.

The Senior Skills example visual gate was run and correctly returned BLOCKED_UNVERIFIED_DESIGN; its draft lacks verified asset licenses. That result is framework evidence, not a project-specific visual pass. Actual screenshots, app-commit binding, keyboard/RTL checks, and task observations are required before release readiness.

## Next acceptance boundary
Run a real small video with valid calibration, download every output across reruns, and measure process memory below the safety ceiling before public hosting.

Rollback: revert this milestone branch before merge. Do not merge or deploy automatically. Future runs must inspect open PRs and continue this branch before creating duplicate work.
