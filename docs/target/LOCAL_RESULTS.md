# Executed local checks — 29 September 2026

The application change is local only. GitHub and the live Pages website are unchanged.
The existing native physical equations and seven original scenes are byte-preserved.

## Observed results

- 89 Python/native tests passed, no failures or skips.
- 25 Node contract tests passed, no failures or skips.
- 12 browser checks passed on the self-authored private HTML loaded into memory. They exercised the four actual supplied reference crops, six generated comparisons, exact sample/file hashes, playback, paused-seek rejection, original WAV downloads, feedback export and desktop/mobile layouts.
- Normal HTTP and file navigation were blocked by the browser administrator. These are not reported as passes, and no browser security policy was disabled.
- The public build contains 24 allowlisted files and no user recording waveforms.
- `assess_target_study.py --require-target` returns **2**: the target acceptance gate is intentionally unmet, based on the documented missing requirements and measured mismatches. The policy is not a calibrated listener threshold.
- No human listening ratings or new LLM-subagent reviews were produced. Automated test observations are not listener evidence.

[Local receipts](../../validation/target/local-audit.json) identify execution scope and unchanged sources. [Browser evidence](../../validation/target/browser-memory.json) records each check; [target discrepancies](../../validation/target/target-readiness.json) retain the failed model comparisons. Historical failed navigation attempts are preserved in the adjacent reports.

The new empirical source is an unaccepted acoustic comparator, not an implemented tongue/saliva/ear physical system. Unit tests, playback, a website build and exact file hashes do not certify the requested sound quality.
