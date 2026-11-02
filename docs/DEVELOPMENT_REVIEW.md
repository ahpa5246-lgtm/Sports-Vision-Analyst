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

## Verification update — 2026-10-31

Scope: existing draft PR #2, branch `codex/persistent-analysis-workspace`, verified head before this documentation update: `50d9e1055187f519459bc3408fdbbedae6cbb6d8`.

### CI and functional evidence

| Check | Observed result |
| --- | --- |
| Streamlit browser journey | Passed on Chromium at 1440×1000 and 768×900 |
| Upload → analyze → results → clear | Passed with a real licensed two-second football clip |
| Annotated video playback | Passed at both widths; desktop currentTime 0.5178s, narrow currentTime 0.5128s, readyState 4, no media error |
| Result persistence across Streamlit rerun | Passed |
| Narrow horizontal overflow | False |
| Real-model smoke | Passed on CPU with YOLO26n + ByteTrack; 8 frames processed |
| Browser journey inference evidence | 16 frames processed; 67 tracking rows |
| Peak RSS in real-model smoke | 1,198,711,880 bytes |
| CI runs | [push run 41229687215](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41229687215) and [pull-request run 41229690908](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41229690908): both passed |

The browser evidence artifact records a CC BY-SA 4.0 Wikimedia Commons source clip, its SHA-256, the prepared clip hash, frame counts, download sizes and viewport screenshots. Neither the source clip nor the annotated output video is uploaded. The annotated download is now `annotated.webm`; the result bundle carries the correct `video/webm` MIME type.

### Defect found and corrected

The previous `mp4v` output rendered an HTML video element but Chromium rejected playback with `NotSupportedError`. A screenshot of the player was therefore not evidence of working playback. The pipeline now prefers VP9 WebM and falls back to VP8 WebM; the result bundle validates the filename and derives the MIME type. Browser acceptance now requires at least 0.5 seconds of actual playback at both desktop and narrow widths. The resulting evidence reports 0.5178s and 0.5128s respectively, with `readyState=4` and no media error.

### User journeys and visual comparison

The application keeps three distinct destinations: **Analyze** (upload and run), **Results** (video, pitch overlay, metrics and downloads), and **Calibration guide** (instructions for the current CLI calibration path). The separation is coherent for the current local, single-camera scope, but the calibration destination is documentation rather than an in-app guided calibration workflow.

Reviewed published product interfaces:

- [Hudl Sportscode](https://www.hudl.com/products/sportscode) — its official coding-window capture combines video, a synchronized timeline, player/event buttons and structured coding output. The current app has a working annotated video and pitch overlay, but no event-coding timeline or linked player/event report.
- [Kinovea](https://www.kinovea.org/) — its official analysis and measurement screens prioritize frame navigation, video annotation, measurement overlays, synchronized comparison and export. The current app has a useful overlay and downloadable CSV, but lacks manual annotation, frame-by-frame review controls and side-by-side video comparison.
- Official visual/product reference: [FIFA Football Data Platform](https://inside.fifa.com/innovation/innovating-the-game/football-data-platform). FIFA describes a unified analysis environment with multiple visualizations and data/video synchronization. This is a reference for keeping match data, video and analysis in one coherent workspace, not a feature-equivalence claim.

The current UI is a functional Streamlit prototype rather than a visual match for those professional tools. The next meaningful UI milestone should address the analysis workflow (timeline/event inspection and guided calibration) rather than a color-only redesign.

### Remaining limitations

- The real-model check uses a short, low-resolution sample; it does not validate full-match throughput or tracking accuracy across representative camera angles, occlusion, lighting and pitch conditions.
- Calibration is still a CLI workflow; the in-app guide does not perform calibration.
- No side-by-side comparison, manual telestration or event timeline is implemented.
- The current 768px viewport check is a narrow-browser check, not a complete mobile-device or assistive-technology audit.
- The two workflow triggers currently run equivalent CI on both push and pull_request events; this consumes duplicate CI time and should be consolidated in a separate workflow-only change.

No merge, deployment or production claim was made. PR #2 remains a draft.

## 2026-11-01 — CI trigger scope and fresh end-to-end evidence

### Workflow trigger correction
The workflow change at branch commit `479ee19e79e26b7592218c87972f5629cc350eb5` scopes `push` to `main` and `pull_request` to PRs targeting `main`. Feature-branch pushes therefore do not start a second workflow alongside the PR checks. A later push to `main` remains a separate post-merge validation event; the two events are not interchangeable because they validate different refs. This supersedes the earlier blanket statement that every feature-branch push and pull-request update duplicated the same CI run.

### Current PR-head evidence
- PR head: `479ee19e79e26b7592218c87972f5629cc350eb5`.
- Pull-request workflow run [41241290173](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41241290173): both jobs passed.
- `test`: dependency installation, Pytest and compileall passed; Pytest reported 9 passed and 2 skipped. The skips remain visible and are not counted as passes.
- `real-inference-smoke`: real YOLO26n + ByteTrack CPU inference passed on 8 generated frames; the result bundle contained `annotated.webm`, `summary.json` and `tracking.csv` (2,930 bytes); measured peak RSS was 1,200,328,704 bytes.
- The licensed-footage Streamlit browser journey passed, including upload, analysis, results, rerun and downloads. Evidence artifact [13057736521](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41241290173/artifacts/13057736521) was uploaded (624,735 bytes).

### Limits unchanged
This run verifies pipeline execution and the short browser journey, not full-match detection accuracy, player identity, broadcast-camera robustness or match-scale throughput. It does not implement in-app point selection/calibration, event timeline, manual telestration or side-by-side comparison. Hudl Sportscode and Kinovea remain the direct released-product references; FIFA Football Data Platform remains the official aspirational reference. The comparative review is task-level and the visual-quality gate remains unpassed until the actual app screenshots are bound to the implementation audit and inspected as required. No merge or deployment.


## 2026-11-01 — inspect current PR-head inference and UI evidence

### Current-head CI and artifact binding
- Reviewed PR #2 at branch head `f5952aadb01088f068fef66e8c6c6fc00072007b`; the PR remains open and Draft.
- GitHub Actions PR run [41246081081](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41246081081) completed successfully. Both `test` and `real-inference-smoke` jobs passed, including the licensed-footage Streamlit browser journey.
- Artifact [13058613434](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41246081081/artifacts/13058613434), `real-inference-and-ui-evidence-f38ade63da8856672351a2341a5c54e55660423c`, was downloaded and inspected. Archive size: 625,659 bytes; GitHub artifact digest: `sha256:53b51638cf5f5e721504f61115a839fff3588a34e9d35acbc557d2a3994b123e`. It contains the real-inference JSON, five UI screenshots, attribution JSON, results JSON, and the Streamlit log.

### Real-model smoke evidence
- Model: `yolo26n.pt`; tracker: `bytetrack.yaml`; device: CPU.
- Eight generated frames were processed. The downloadable bundle contained `annotated.webm`, `summary.json`, and `tracking.csv`, totaling 2,930 bytes.
- Recorded peak RSS: 1,195,126,784 bytes on this GitHub runner.
- This remains a bounded model/tracker plumbing check. It is not full-match accuracy, ball detection, identity verification, broadcast-camera robustness, or a hosting-memory recommendation.

### Browser journey and inspected screenshots
- The real licensed Wikimedia Commons clip was prepared from [Street football 2](https://commons.wikimedia.org/wiki/File:Street_football_2.webm) by Anasskoko under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The artifact records source and prepared-clip SHA-256 values and the exact two-second, 640×360, 8-fps, audio-free transformation.
- The Streamlit journey processed 16 frames and produced 67 tracking rows. It verified Analyze upload → analysis completion → Results → Calibration guide → Results → downloads → Clear results.
- Downloads were nonempty: `tracking.csv` 4,888 bytes, `summary.json` 2,545 bytes, and `annotated.webm` 207,327 bytes.
- Actual Chromium playback advanced 0.5238 seconds at 1440×1000 and 0.5077 seconds at 768×900; both reported `readyState=4` and no media error. The Streamlit rerun preserved the result, and the 768px page had no horizontal overflow.
- I inspected `analyze-uploaded.png`, `analyze-complete.png`, `results-desktop.png`, `results-narrow.png`, and `results-cleared.png`. The screenshots are bound to this PR-head workflow artifact, not to a local mock. The Calibration guide was visited by the test but no dedicated screenshot was captured, so its visual hierarchy is not yet evidenced.
- The initial video-element snapshot recorded `readyState=0` before playback was requested; the subsequent measured playback above is the acceptance result. Do not interpret the pre-playback snapshot as a failed video.

### Updated product comparison and observed gaps
- [Hudl Sportscode](https://www.hudl.com/products/sportscode) remains the direct coding-workflow reference: its official product material shows synchronized video, a timeline, coding buttons and structured player/event output. The current Results screenshot is dominated by one annotated video and three aggregate metrics; there is no synchronized event timeline or player/event coding surface.
- [Kinovea](https://www.kinovea.org/) remains the direct analysis/measurement reference: its released interface emphasizes frame navigation, measurement overlays, annotation and synchronized comparison. The current app proves playable annotated output and downloads, but the screenshot shows no frame-step/scrub controls, manual telestration or side-by-side comparison.
- [FIFA Football Data Platform](https://inside.fifa.com/innovation/innovating-the-game/football-data-platform) remains the official aspirational reference for coherent match data, video and analysis. The current prototype is narrower and should not imply feature equivalence.
- The inspected 1440×1000 and 768×900 Results screens preserve the video without horizontal overflow, but the video consumes most of the first view and the three metrics remain the only visible summary. The Analyze screen has a clear upload/action sequence and collapsible detection settings. The Calibration guide is still CLI instructions rather than an in-app calibration workflow.
- Decision: do not add decorative polish. The next product milestone should be a bounded frame-review workflow using the existing annotated video and tracking output, with explicit frame/time selection and a useful player/track detail view. Do not label tracks as verified player identities or invent semantic events from raw tracking rows. Guided point calibration remains a separate later milestone because it changes the data-entry and homography workflow.

### Remaining limits
- No full-match footage, ground-truth annotations, ball detection, accuracy benchmark, repeated camera-angle evaluation, or real-user study was performed.
- No in-app calibration editor, event timeline, manual annotation, synchronized side-by-side comparison, or screen-reader/keyboard audit is established by this artifact.
- The screenshots verify the tested Streamlit journey only. They do not pass the full comparative visual-quality gate or establish release readiness.
- No merge or deployment.


## 2026-11-01 — measurement-integrity dependency and current-head verification

### Current PR-head CI
- Reviewed PR #2 at head `4bf78a950a0168f89407241b0504a76634912c4c`; it remains open and Draft.
- GitHub Actions PR run [41265928286](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41265928286) completed successfully on that head.
- The `test` job passed dependency installation, Pytest and `compileall`. The `real-inference-smoke` job passed YOLO26n + ByteTrack CPU inference and the licensed-footage Streamlit browser journey through upload, analysis, results, reruns and downloads.
- Artifact [13067345876](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41265928286/artifacts/13067345876) was uploaded (625,212 bytes; SHA-256 `0376d91b581833ef1c20a2990a3c1cfd6228187ec53d8e41872557cd738073c3`).
- Passing inference and browser checks do not establish measurement-integrity coverage; the issue below is not exercised by those jobs.

### Confirmed P1 measurement-integrity blocker
- Re-read `sports_vision/analytics.py` at PR #2 head. `PlayerAccumulator.update` still increments `samples` and overwrites `last_position` / `last_time_s` without first rejecting non-finite timestamps/coordinates or non-increasing timestamps.
- A NaN/Inf sample can poison the previous-sample state; an out-of-order sample can rewind it. The next valid interval may then be skipped or calculated from an invalid baseline.
- The exact issue is already recorded in the owner's [PR #2 review comment](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/pull/2#issuecomment-6553391611).

### Existing fix — do not duplicate
- Open Draft PR [#3](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/pull/3), branch `codex/portfolio-quality-2026-10-25`, head `2e0810061d24fa2c9312c94c47df092b444da45b`, already rejects non-finite and out-of-order samples and adds `tests/test_measurement_integrity.py`.
- PR #3 CI [40200781849](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/40200781849) passed.
- PR #3 also changes `README.md`, adds `docs/QUALITY_REVIEW.md` and `docs/project-overview.svg`; it is not a two-file patch that can be blindly merged into PR #2.
- Do not copy the guard/tests into PR #2 while the existing PR #3 remains the source of the same fix. Reconcile the two existing branches so the guard and regression tests land exactly once, then rerun the unit suite, real-inference smoke and Streamlit browser acceptance on the resulting PR #2 head.

### Gate decision at the time of the initial review
PR #2 remained Draft and was not ready for measurement-integrity sign-off at that snapshot. The blocker was subsequently addressed on the existing PR #2 branch; see the verified integration entry below. No merge or deployment was performed.


## 2026-11-01 — measurement integrity guard integrated into PR #2

### Branch reconciliation
- PR #2 was reviewed at head `31d0eae1992eb0dcbd28d7d47fc3a415bd1fd7bb`; its `PlayerAccumulator.update` still mutated the previous sample without finite-value or monotonic-time validation.
- Existing Draft PR #3 (`2e0810061d24fa2c9312c94c47df092b444da45b`) already contained the minimal guard and a regression test, but also carried separate README, quality-review and illustration changes.
- Only the measurement guard and its regression coverage were transferred to the existing PR #2 branch. No new branch or PR was created, and the unrelated PR #3 documentation/illustration changes were not copied.

### Implementation
- Reject a sample unless its timestamp and both coordinates are finite.
- Reject timestamps that are not strictly later than the previous accepted sample.
- Perform both checks before changing team, sample count, previous position/time, distance, or speed state.
- Regression tests cover NaN/positive infinity timestamps, NaN/infinite coordinates, out-of-order samples, and preservation of the last accepted tracking state.

### Verification
- Implementation commit: `bda72a0a67ff485a79e381e6da7378d954df1f96`.
- GitHub Actions run [41308755104](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41308755104) passed on this exact PR #2 head; both `test` and `real-inference-smoke` jobs completed successfully.
- `python -m pytest`: 15 passed, 2 skipped. `python -m compileall sports_vision app.py`: passed.
- Real model smoke: YOLO26n + ByteTrack on CPU, 8 generated frames, 2,930-byte result bundle, peak RSS 1,197,674,496 bytes.
- Streamlit browser journey: 16 licensed-footage frames processed and 67 tracking rows; downloads were tracking.csv 4,889 bytes, summary.json 2,545 bytes and annotated.webm 207,327 bytes. Video playback reached 0.5137 s at 1440×1000 and 0.5078 s at 768×900, both with `readyState=4` and no media error. A rerun preserved the result and the narrow page had no horizontal overflow.
- Artifact [13084338209](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41308755104/artifacts/13084338209) (625,232 bytes) was downloaded; I inspected the actual desktop and narrow results screenshots. The UI is unchanged by this analytics-only milestone.
- The subsequent review-document head `f01bc1f34a4fbb41dabd0582864ceefa80e85367` passed CI run [41309065068](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41309065068); both declared jobs passed.

### Remaining limits
- This guard protects accumulator state from malformed or out-of-order samples; it does not establish detector/tracker accuracy, player identity, full-match validity, or measurement calibration accuracy.
- The existing PR #3 still contains the same guard on its separate branch. Keep both PRs unmerged until the duplicate review path is reconciled; do not copy this fix elsewhere.


### Remaining acceptance after the verified guard
- The P1 accumulator-state corruption path is covered and green on PR #2. This does not establish full-match detector/tracker accuracy, player identity, calibration accuracy, or representative camera robustness.
- PR #3 was subsequently narrowed to documentation-only at head `56120d305a51b429ccd444b133cd438eaf467419`; `sports_vision/analytics.py` now matches `main`, and `tests/test_measurement_integrity.py` is absent from that branch. Its current-head CI run [41309250371](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41309250371) passed. The guard and regression tests now exist only on this active feature branch.
- In-app calibration, event timeline, manual telestration, synchronized side-by-side comparison, screen-reader/keyboard audit and full-match ground-truth evaluation remain open.


## 2026-11-01 — narrow Frame review radio interaction repair (validation pending)

### Failure-first review
- Current PR #2 head before this repair: `c2f69208207a7feddaa8ef8d0e4c1f207282cf35`.
- GitHub Actions run [41323604500](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41323604500) failed in the `real-inference-smoke` job at **Exercise upload, analysis, results, reruns and downloads in Streamlit**. The separate unit-test/compile job passed, and the eight-frame real-inference smoke passed.
- The test source showed that the desktop review-mode path used the visible-label helper, but the later 768px narrow path still called Playwright `.check()` directly on Streamlit radio inputs. The same visible-label helper is now used for both narrow-mode transitions. This is a test-interaction correction; no production application or analytics code changed.
- The connector exposed the failed job and step but not its Playwright stack trace. The diagnosis is therefore code-based; the new current-head browser run is the acceptance authority.

### Repair and pending evidence
- Replaced both remaining direct radio `.check()` calls in the narrow journey with `select_review_mode(...)`, which clicks the visible option label and asserts the selected radio state.
- The journey still verifies Frame review content, Track ID selection, dataframe visibility, and no horizontal overflow at 768px.
- **Validation completed:** current head `005a5943445521f08f9fdd8d1884c33b44e5aa2d` passed both CI jobs in run [41326576964](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41326576964); the browser artifact was downloaded and inspected. See the final verification entry below.

No merge or deployment. Keep PR #2 Draft.


## 2026-11-01 — narrow Frame review repair verified on the current PR #2 head

### Current-head CI
- Final test commit: `005a5943445521f08f9fdd8d1884c33b44e5aa2d`.
- GitHub Actions run [41326576964](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41326576964) completed successfully on that exact head. Both `test` and `real-inference-smoke` jobs passed; the previously failing browser step **Exercise upload, analysis, results, reruns and downloads in Streamlit** is green.
- Unit job: `python -m pytest` and `python -m compileall sports_vision app.py` passed.
- Real inference: YOLO26n + ByteTrack on CPU processed 8 frames; evidence bundle 2,930 bytes; peak RSS 1,196,224,512 bytes.
- Evidence artifact [13091785768](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41326576964/artifacts/13091785768), 957,511 bytes, SHA-256 `4321557b199d2c58851bc12f6a83eb9f7236b54d41867055a86eff35a7dd2377`, is bound to the tested PR head.

### Actual browser acceptance
- The Streamlit journey completed upload, analysis, results, video playback, Frame review, calibration-guide navigation, rerun persistence, CSV/JSON/video downloads, and clear-results behavior.
- The real-footage run processed 16 frames and produced 67 tracking rows. Downloads: tracking CSV 4,888 bytes, summary JSON 2,545 bytes, annotated WebM 207,327 bytes.
- Video playback advanced 0.5205 seconds at 1440×1000 and 0.5087 seconds at 768×900; both reported `readyState=4` with no media error.
- Frame review verified the selected-frame heading, frame slider, Track ID control, tracking table, and keyboard interaction. Both 768px results and Frame review reported no horizontal overflow; rerun preserved the result.
- Downloaded and inspected `frame-review-narrow.png` (768×900) and the desktop/narrow results captures. The narrow screenshot shows the selected Frame review state, frame index control and tracking table; the page remains vertically scrollable without horizontal clipping.

### Product comparison and remaining gaps
- [Hudl Sportscode](https://www.hudl.com/products/sportscode) is the direct team-analysis reference for customizable performance analysis and linked replay/telestration workflows. [Kinovea](https://kinovea.org/features.html) provides frame/time navigation, annotation, measurement, and synchronized two-video comparison. [FIFA Football Data Platform](https://inside.fifa.com/innovation/innovating-the-game/football-data-platform) is the official visual/data reference for unified match events, statistics, and video synchronized with events.
- The current app's real workflow is still Analyze → Results → Video playback/Frame review. It now verifies the frame-review path, but it still lacks an event timeline, manual telestration, synchronized side-by-side video comparison, and in-app calibration editing. Do not claim parity with Hudl or Kinovea.
- This repair changed only the browser test and review record, not production UI or analytics. Measurement-integrity guard remains in PR #2; the earlier failure run [41323604500](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41323604500) is superseded by the successful current-head run above.
- Keep PR #2 Draft. No merge, deployment, release, or model-accuracy claim.


## 2026-11-02 — migrate CI actions to Node 24-compatible releases

### Failure-first evidence
- Existing PR #2 head before this maintenance stage: `a163fd8a952717c3647cb5be2be3e98d6f32a9ca`.
- PR CI run [41327147864](https://github.com/ahpa5246-lgtm/Sports-Vision-Analyst/actions/runs/41327147864) completed successfully for both `test` and `real-inference-smoke` jobs, but both job logs emitted GitHub's Node.js 20 action-runtime deprecation warning. The warning names `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/upload-artifact@v4`; it is a maintenance warning, not an application-test failure.
- Python 3.11, the application dependencies, model smoke, licensed-footage browser journey and artifact contract are unchanged by this stage.

### Bounded workflow change
- `actions/checkout` is updated from v4 to v7.
- `actions/setup-python` is updated from v5 to v6.
- `actions/upload-artifact` is updated from v4 to v7.
- Official action metadata was inspected at [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-python v6](https://github.com/actions/setup-python/releases/tag/v6.0.0), and [upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2); each JavaScript action declares `runs.using: node24`.
- No application source, Python version, dependency, test command, model, calibration, or deployment workflow was changed.

### Validation pending
- Documentation checkpoint: this entry records the observed warning and the planned bounded action migration.
- The following workflow-only commit is the implementation checkpoint. Its exact PR-head CI must pass both jobs, including real YOLO26n + ByteTrack CPU inference and the Streamlit upload → analysis → results → rerun → download journey.
- Do not call this migration verified until the exact-head CI logs show no Node.js 20 action-runtime warning and the evidence artifact is inspected.
- The existing direct-product comparison remains [Hudl Sportscode](https://www.hudl.com/products/sportscode) and [Kinovea](https://www.kinovea.org/features.html), with the [FIFA Football Data Platform](https://inside.fifa.com/innovation/innovating-the-game/football-data-platform) as the official event/video reference. This CI maintenance change does not alter the UI and does not close the event-timeline, manual-telestration, synchronized-comparison, in-app-calibration, accessibility, or full-match ground-truth gaps.

Keep PR #2 Draft. No merge, deployment, release, or model-accuracy claim.
