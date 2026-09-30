# Binaural main deployment and live verification

Verified 30 September 2026. Application commit: `51f8390e6687d590ca53c8e9f97221d9d6807f67`.

## Actual build and deployment

- [Full main CI 36762593351](https://github.com/parafieldai/Ku100-Sim/actions/runs/36762593351) completed successfully, including native/Python tests, all existing generation pipelines, receiver checks and browser suites.
- [Pages publication 36764267475](https://github.com/parafieldai/Ku100-Sim/actions/runs/36764267475) completed successfully. The actual `deploy` job and `actions/deploy-pages` step succeeded, not merely a Pages-availability check.
- [Live verification 36764340185](https://github.com/parafieldai/Ku100-Sim/actions/runs/36764340185) completed successfully against the public HTTPS site. All legacy and new live-browser steps succeeded.

The new binaural examples are available at:

- https://parafieldai.github.io/Ku100-Sim/unified/ — seven shared-mechanics scenes.
- https://parafieldai.github.io/Ku100-Sim/objects/ — nine measured-profile object-tap comparisons.

The source-texture page remains at `/source/`, with its public source-only/mono mode removed. Existing microphone-domain texture algorithms are not relabeled as a new measured capture model.

## What was independently checked from the downloaded artifacts

Both final artifacts were downloaded, their full SHA-256 hashes matched GitHub's declared digests, and every ZIP member CRC passed.

| Artifact | ID | Bytes | SHA-256 |
|---|---:|---:|---|
| Main | 11119801625 | 108950179 | `e58cac503eef1237ac9d83e10f04be375aa2789363b529cbdeb9091d2dd2bba8` |
| Live | 11119384245 | 5918767 | `9e1b748e76078e4272027dead063c9a59ad1c6100f9b8729062ac892f786ebe9` |

All sixteen new main WAVs match their manifests and are byte-identical to the previously verified branch/local renders. Every example has two active, nonidentical ear channels. Their measured receiver bank identity is `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712`.

Chromium 151.0.7922.34 reported:

| Live suite | Assets matched to the exact main artifact | Audio examples |
|---|---:|---:|
| Shared mechanics | 25 | 7 |
| Object taps | 13 | 9 |
| Existing source textures | 13 | 7 |

The listed live asset hashes were independently compared with the downloaded main archive, not just checked against each report's own expected field. All returned HTTP 200. Tests exercised playback, completed seeking, original WAV downloads, nonidentical ear samples, exclusive playback where applicable, and desktop/mobile layouts without application errors. The source page passed the explicit no-public-mono check. Edited shared scenes retain receiver parameters, and editing does not falsely alter precomputed playback.

The object page retains its explicit Float32 listening preview of the original PCM16 sample codes. Those preview samples agree exactly; direct browser PCM decoding can differ by a quantization step and is separately reported. Original PCM16 WAV downloads remain unchanged. The seven shared-engine WAVs decode exactly through their tested playback path.

The implementation validation passed 191 native/Python tests and 25 frontend tests, including 18 added receiver tests. The new receiver was compared with independently decoded measured filters, static full convolution and a separately assembled moving-filter reference. These checks establish implementation agreement, not an ASMR listening verdict. See [CLOUD_RESULTS.md](CLOUD_RESULTS.md).

## Scope and unresolved sound quality

All sixteen previews now pass through the same `BinauralMicrophone` implementation. Their left/right differences come from measured KU100 responses and the declared source path, not duplicate mono, independent channel normalization or an arbitrary stereo-widening effect.

The default measured radius is 0.25 m from the dummy-head center. This is an airborne point-source approximation, not an ear-touching measurement. The implementation does not claim 3Dio calibration, direct contact/seal transmission, rotating-fork quadrupole radiation, or identified plastic/silicone source timbre. The inherited coloration of measured object profiles is disclosed separately from the added receiver. The mechanical velocity readout is not assigned calibrated pressure units.

The user's negative evaluation of the source sound remains unresolved. No human listening judgment is filled in, and no newly spawned LLM-subagent audit is claimed. Stereo capture fixes a required output stage; it cannot certify ASMR sound character by itself. Source performance recordings were not published or replayed in these renders; measured receiver impulse responses are explicitly identified research data.

Local browser navigation was blocked by administrator policy and was not bypassed. HTTP/live browser findings above come from the GitHub-hosted runs and inspected artifacts, not a claimed local navigation test.

Legacy statistical generators were rerun by the full main pipeline. Unchanged algorithms and models do not imply byte-identical optimizer-derived historical waveforms; no such preservation claim is made here.

## Documentation-only follow-up

Commit `da55d759978696ec19d64d47e37aaeb916327d50` corrects the dataset author's name to Annika Neidhardt and narrows the browser-test description to preservation of receiver configuration in edited scenes. It changes no executable code, scene, waveform or workflow. This receipt also changes documentation only. Both use `[skip ci]`; the actual tested/deployed application remains the `51f8390` commit named above.

See [BINAURAL_CAPTURE.md](../../docs/engine-rebuild/BINAURAL_CAPTURE.md) for equations, API, dataset attribution and all measurement limits.
