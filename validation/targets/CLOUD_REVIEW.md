# Target-source investigation: executed cloud verification

29 September 2026. The full wet-contact target remains **not met**. These checks establish software behavior, bounded numerical source accuracy and preservation/privacy of a comparison workflow, not realistic tongue/saliva sound.

## Exact source

Tested expanded source commit: `ea0296e6854717a0bd0ca7f3864fc6549a470b3b`.

Successful GitHub-hosted [run 36640966536](https://github.com/parafieldai/Ku100-Sim/actions/runs/36640966536). It validated the exact 26-file source patch before applying it, built both source families, and published the tested source on `target-source-review` without force. The temporary source-transfer files were removed from that source tree. The temporary workflow is removed in the final integration; the same checks are incorporated in regular main CI.

The downloaded artifact `target-source-review-36640966536` has 42,635,982 bytes and SHA-256:

```
428c9b6f83b9a145cbf3fc2dc597fcdd6cf80aff0f132eb2ee1e0603c8ad6191
```

All ZIP CRCs passed. Every one of the 26 patched source/document files in the embedded source archive is byte-for-byte identical to the locally inspected source. Generated source files do not contain target recording samples. The artifact contains generated audio, derived target measurements, tests, reports, screenshots and the exact tested source, not raw target WAVs.

## Executed checks

- 87 native/Python tests passed, including six new release-source tests and six publication-boundary tests.
- 19 original frontend tests passed.
- Original contact/receiver/refinement and viscous-component tests remained passing; their scope and weak-band limitations are unchanged.
- New pressure-release reference: the independent linear 3-state matrix exponential retains failures at 192 and 384 kHz; 768 kHz meets its 0.5% final-state criterion. The nonlinear, viscous-memory source has a separate 384-to-768 kHz waveform refinement comparison.
- Original seven-example browser and offline suites passed.
- Seven target-comparison HTTP browser groups passed: four source WAV identities/playback; local synthetic-reference import preserving channel order; blank judgments and exact review identifiers; exclusive A/B playback; malformed input rejection/no upload; explicit rejected baseline/research-only statuses; desktop/mobile layout.
- The same seven groups passed for the generated-only offline target page.
- Browser was Chromium 151.0.7922.34. No uncaught browser errors were recorded.

The browser's synthetic import fixture exercises software input handling. It is **not** a perceptual comparison or claim of hearing the user's target recordings. The private optional HTML package with actual user excerpts is not uploaded to GitHub or Pages. Local browser navigation in the assistant container was blocked by administrator policy; the successful browser results above are from GitHub-hosted execution.

## Scientific outcome retained

The fixed target cuts contain substantially greater sustained activity and detector-event density than the sparse pressure-release example. The component is explicitly rejected as a complete target model. Prescribed opening is not a solved tongue/film/peeling action; all source geometry is assumed. The measured 25 cm airborne KU100 receiver does not validate direct wet-ear transmission. No source mechanism has been identified in the supplied target and no listener score is prefilled.

See [target refocus](../../docs/TARGET_REFOCUS.md), [SFX research](../../docs/SFX_TRIGGER_RESEARCH.md), [numerical component evidence](release-validation.json) and [source-study measurements](source-study.json).

Main CI, deployment and public-HTTPS checks must each be verified at their actual later run. This source-validation receipt alone is not a deployment receipt.
