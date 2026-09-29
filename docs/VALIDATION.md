# Executed validation and remaining failures

This evidence concerns the C++ contact-coupon prototype, not the earlier README-only repository. The final native source SHA-256 is `e5142ef49e088a3ea7116fcd3c25153b24a9dc2e2c43c7611348cfe72d9da1c7`.

## What passed locally

| Check family | Executed result | What it establishes |
|---|---|---|
| Native CLI and separately assembled ODE reference | 67 acceptance checks passed | Finite stereo export, input rejection, replay, physical parameter effects, energy accounting and stated high-resolution linear-reference accuracy |
| Native component invariants with AddressSanitizer and UndefinedBehaviorSanitizer | 13 checks passed | Convolution tails, decimation latency, separately actuated left/right symmetry, moving-contact work and discrete potential identities; no sanitizer findings in these tests |
| Measured KU100 convolution vs SciPy convolution | 149.52 / 151.61 dB numerical SNR | Per-channel implementation agreement, not recording realism |
| Rigid-sphere benchmark | Series relative difference 2.17e-10; static-limit magnitude error 5.63e-9 | Series convergence and analytic limits for an ideal sphere |
| Chromium offline viewer | 7 checks passed | Actual audio playback, seeking and telemetry, scene export, scene switching, mobile layout and absence of uncaught JavaScript errors |

Across the 16 native audit renders, the largest normalized work-energy residual was 7.83e-12. This small numerical residual does not identify a device's material properties or establish audible realism.

## Accuracy failures remain visible

The strict linear free-decay test compares the final state after 0.21 seconds against a separately assembled continuous ODE and matrix exponential. The error norm is energy-weighted and relative to the exact remaining state; it is not a listening score or a whole-signal error.

| Internal oversampling | Relative final-state error | Meets the 0.5% target? |
|---|---:|---|
| 4x | 48.87% | No |
| 8x, native default | 12.87% | No |
| 16x | 3.23% | No |
| 64x, separate reference-quality test | 0.202% | Yes |

Refinement ratios are approximately four, supporting second-order convergence for the linear test. The lower-rate failures are retained in `research/initial-accuracy.json`; they were not changed into passes by weakening their threshold. The 67-check acceptance suite explicitly tests the 64x configuration and preserves the lower-rate diagnostics.

For a separate nonlinear stroke waveform, the 8x result differs from 16x by 0.318% in relative waveform norm. This is a different test and does not erase the free-decay failure.

Spatial refinement is not complete: the default 6x6 modes per ear differ from 12x12 by 14.25% in waveform norm; 8x8 still differs by 9.07%. The thin-plate assumptions themselves need scrutiny at higher mode orders. No converged 20 kHz anatomical simulation is claimed.

## Comparison with recordings

The measured KU100 receiver route preserves both channels of the actual airborne response. A separate ideal-sphere benchmark differs from the 25 cm, 90-degree measured interaural level difference by approximately 1.90 dB (200-1000 Hz), 6.57 dB (1-4 kHz), and 19.99 dB (4-8 kHz). That is a reason not to substitute the sphere for measured pinna/head responses.

The default generated left-contact scene places about 97.4% of selected-ear 20 Hz-20 kHz power below 250 Hz. The fixed six-second center excerpt of supplied chapter 06 has about 74.1% of left-channel power in 1-4 kHz, versus about 0.61% in the simulation. These are unpaired, uncontrolled examples with unverified reference microphone provenance, not a valid matched-action fidelity score. They nevertheless show that passing software tests does not establish the requested contact sound.

The model's approximately 36.4 dB overall channel separation depends on an assumed structural spring. It is not a measured KU100 transmission path and must not be tuned solely to make that number resemble a performance recording.

## Browser and cloud boundary

The local environment blocked HTTP browser access. Testing used the fully embedded native-output companion in Chromium instead. No browser security policy was changed. Offline playback and interaction passed; HTTP hosting and a deployed GitHub Pages URL have not passed end-to-end verification.

GitHub accepted and triggered the Native verification workflow, but run `36529482606` failed before exposing any job steps. Its log retrieval returned BlobNotFound. The cause is not established. This is not reported as a successful cloud test. A Pages workflow is provided, but a committed workflow is not a live deployment; Pages must be enabled and GitHub-hosted execution must work.

No subagent invocation tool was available in this continuation. The reference code is separately assembled, but these results are not represented as independent subagent review. No human listening assessment or ASMR-response assessment was conducted.

## Reproduce

```sh
python tests/verify.py
python tools/sphere.py
python tools/compare_receivers.py
clang++ -O1 -g -std=c++17 -fsanitize=address,undefined -fno-omit-frame-pointer tests/dsp.cpp -o build/dsp_sanitized
ASAN_OPTIONS=detect_leaks=1 ./build/dsp_sanitized
python tools/build_site.py --out _site
python tests/browser.py --site _site --offline --chromium /path/to/chromium
```

The repository includes a compact evidence summary and reproducible tests. Detailed JSON reports are generated by these commands. Additional local receiver comparisons used six extracted directions from the two recovered SOFA circles; the repository vendors one disclosed receiver fixture.
