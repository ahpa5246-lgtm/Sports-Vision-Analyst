# Sports Vision Analyst: engineering review, 2026-10-18

## Scope and intent
Owner requested continued implementation and severe comparison with released products. This is the first bounded repair milestone, not a full completion claim. Local/offline architecture is retained; no new paid service or deployment.

Core journey: Upload → calibration → analysis → results/downloads.

## Decision and implementation
Separate Analyze, Results, Calibration guide. Keep completed output bytes in Streamlit session state after temporary cleanup, publish only complete bundles and preserve earlier results on analysis failure. Uploaded video names no longer control local paths.

Alternative: decorate the existing home page while leaving workflows and state bugs unchanged. Rejected because appearance cannot repair lost results or crowded controls. Existing architecture remains intact.

## Reference research
Official feature/product pages consulted for task hierarchy and separation of primary work from setup/reference. No source, artwork, icon or layout copied:
https://www.hudl.com/products/sportscode
https://kinovea.org/
https://www.hudl.com/

Web-text inspection is not a visual screenshot comparison. These sources are a starting shortlist, not completed visual evidence. Do not mark the comparative design gate passed. A missing or inaccessible visual reference remains an open item.

## Evidence and harsh self-review
Two unittest cases pass: results survive deleted working directory; report traversal rejected. Python compilation passes. Full model inference and Streamlit interaction have not run. Large videos retained in memory can exhaust RAM; persistence ends with the browser session.

The Senior Skills example visual gate was run and correctly returned BLOCKED_UNVERIFIED_DESIGN; its draft lacks verified asset licenses. That result is framework evidence, not a project-specific visual pass. Actual screenshots, app-commit binding, keyboard/RTL checks, and task observations are required before release readiness.

## Next acceptance boundary
Run real small video + valid calibration; download every output across reruns; profile memory before public hosting.

Rollback: revert this milestone branch before merge. Do not merge or deploy automatically. Future runs must inspect open PRs and continue this branch before creating duplicate work.
