# Measured binaural object capture: pre-integration evidence

30 September 2026. Requirement: every object preview must use a binaural microphone receiver; duplicated mono is no longer an acceptable user-facing result. This report does not claim an ASMR listening pass or a calibrated contact-to-pressure model.

## Executed validation

[Branch validation 36762016812](https://github.com/parafieldai/Ku100-Sim/actions/runs/36762016812) succeeded, including all native tests, regenerated binaural previews, three HTTP browser suites and source-blob publication. No assertions or scientific tolerances were weakened to obtain the pass. Publication assertions intentionally changed from requiring duplicated mono to rejecting it, reflecting the user's corrected requirement.

- **191 Python/native tests passed**, including 18 new measured-receiver tests; zero failures/skips. The complete local suite separately passed the same 191 tests.
- **25 frontend tests passed**.
- **16 object previews** passed the stereo-only receiver and output checks: seven shared-mechanics scenes and nine data-assisted object-tap comparisons.
- Chromium checked seven shared-engine examples and 25 assets, nine object examples and 13 assets, and seven existing source-texture examples and 13 assets. The source-texture public mono switch was removed. Browser checks exercised real playback, completed seeking, downloads, exact decoded samples, no-fake-rerender behavior and desktop/mobile layout.
- Static measured FIRs and full tails agree with an independently decoded bank plus NumPy/SciPy convolution. A separately evaluated output-time varying FIR matches the slow-motion implementation. Measured ear dominance/ITD signs, azimuth wrap, block-size invariance, zero excitation and malformed data are tested.

The branch artifact is `binaural-validation-36762016812`, ID `11118703377`, 18,089,429 bytes. SHA-256:

```
2d7007bdc812d17dcbee1cbc0e0323cf6f6d82beedbdc7bd3478a14ca827d8d1
```

It was downloaded and every ZIP CRC passed. All 30 changed source files' bytes, SHA-256 and Git blob IDs match the locally tested files. The integration uses those exact blobs on the existing main tree; temporary transport files and their workflow are not added to main. This receipt is an additional documentation-only file. Main CI, actual Pages deployment and live HTTPS playback must be checked separately after integration.

## Receiver scope

All object families share `BinauralMicrophone`, backed by `native/binaural/renderer.cpp` and the existing verified KU100 importer/receiver. It is not an object-name dispatch and not independent left/right gain panning. The renderer uses both measured ear filters and full phase/delay history while the specified source direction changes continuously.

The pinned bank SHA-256 is `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712`. Available radii are the measured 0.25, 0.50, 0.75, 1.00 and 1.50 metres, measured from the head center. The default long-enough audition follows a slow right-to-left front arc at 0.25 m; short diagnostic priors remain at a fixed right-side position. One common gain preserves both ears' relationships. There is no second distance-gain correction.

Source movement uses a quasi-static, fixed-radius point-source approximation. The native kernel retains filter tails and state across blocks; it does not solve moving boundaries, rotating-fork directivity, touching/occluding the artificial ear, or 3Dio capsule geometry. Low-frequency receiver extension is partly analytic. Device identity is explicitly KU100, not a generic or relabeled 3Dio.

The shared mechanical readout remains an uncalibrated surface-velocity proxy. The measured object profiles retain their original recording/radiation coloration and are now binauralized approximations; they have not become independently identified emitted sound fields. No force-to-Pa calibration is manufactured. The existing statistical source generators are not used to generate these mechanical sources.

## What did not pass by implication

The user rejected the earlier source character as not producing the intended ASMR SFX. This change fixes missing binaural presentation; no listening judgment has been assigned. Source timbre, geometry/material identification, contact/seal behavior and natural gesture structure remain independent requirements. There was no new human listening test or LLM-subagent review. The local browser's page navigation was blocked; the successful HTTP browser findings above come from the GitHub-hosted runner, not a bypass of that restriction.

Existing ear-texture implementations and fitted parameters are unchanged, apart from removing the public mono mode. Full main CI rerenders old optimizer-derived outputs; exact old-waveform preservation is not inferred from unchanged algorithms. Source model, generated waveform and receiver provenance remain distinct.

See [BINAURAL_CAPTURE.md](../../docs/engine-rebuild/BINAURAL_CAPTURE.md) for the equations, source papers, data/license attribution, API and limitations.
