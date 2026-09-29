# Validation status

## What passed

The integrated native/Python suite passed **59 tests** with no failures or skips, and the frontend suite passed **15 tests**. Independent implementations compare the Mindlin eigensystem, contact forces and complete coupled acoustic/structural step, rather than only checking that the renderer can produce a WAV. The 15-scenario numerical refinement probe also passed its stated checks. Individual suites and their exact scope are recorded in the adjoining audit files.

The full built-site browser run passed **nine end-to-end groups** on Chromium 134.0.6998.35:

1. Load a real native export and compare the browser decoder's stereo samples exactly against the embedded Float32 file.
2. Start audio playback, observe its time advancing, then pause it.
3. Seek into the native trace, use common listening attenuation and operate the geometry controls.
4. Download the original WAV and verify its SHA-256.
5. Edit/export a scene while preserving the loaded audio and its hash.
6. Decode all five real native examples and verify every downloaded WAV hash.
7. Import locally, display an invalid-regime diagnostic, and reject a corrupt audio hash without replacing the loaded render.
8. Check desktop and mobile layouts for horizontal overflow; visually inspect screenshots.
9. Load under a project subpath and verify all assets and playback data resolve.

There were no browser script errors or external network requests. Playback and sample identity were checked by automation. **No human listening or perceived-realism assessment was performed.**

The tested browser used a preinstalled executable because the newer Playwright browser download endpoint returned an HTML availability error in the local environment. CI is configured to install the browser matched to the locked Playwright package and report the actual version it executes. Local browser success does not claim that an unobserved CI run or Pages deployment succeeded.

AddressSanitizer and UndefinedBehaviorSanitizer smoke runs passed dry contact, wet contact and a right-vent airborne case at the formerly problematic negative-epsilon angle. LeakSanitizer could not run under this environment's process tracing; leak detection was disabled for those smoke runs. No leak-clean claim is made.

## Current demonstration renders

These are actual generated 48 kHz stereo Float32 exports. All five passed the conservative physical-regime screens and had zero samples above full scale. [examples.json](examples.json) contains complete scenes, native-source identities and measurements. A shared declared gain is applied to both ears; outputs are not normalized.

| Example | Left RMS dBFS | Right RMS dBFS | L−R dB | Capture gain |
| --- | ---: | ---: | ---: | ---: |
| Dry stroke, left | −25.554 | −29.030 | 3.476 | +20 dB |
| Viscous film, left | −25.230 | −28.390 | 3.160 | +20 dB |
| Tap, right | −26.941 | −22.112 | −4.829 | +20 dB |
| Airborne vent, measured receiver | −51.019 | −56.401 | 5.381 | +90 dB |
| Press/release, left | −26.336 | −29.311 | 2.975 | +20 dB |

The source/capture calibration remains nominal. The airborne example uses an explicitly high ideal gain to make the quiet modeled vent inspectable; a real microphone's self-noise and overload are not simulated.

## Numerical accuracy and physical fidelity are different questions

For the default 0.8 s convergence probe, the maximum energy residual is **1.59×10⁻¹⁸ J** on **1.069×10⁻⁴ J** of actuator work. Mirroring the fixture changes the channel-swapped raw pressures by at most **8.79×10⁻¹⁴ Pa**. Exact silence and zero-load outputs remain zero. The global plate displacement bound is **0.0621 times its thickness**, within the declared default screen.

| Refinement | Left relative waveform L2 | Right relative waveform L2 |
| --- | ---: | ---: |
| 128→256 structural modes | 0.220% | 0.127% |
| 256→512 structural modes | 0.0360% | 0.0307% |
| 512→1024 structural modes | 0.00932% | 0.0131% |
| 192→384 kHz integration | 0.00562% | 0.00661% |
| 32→64 duct cells | 0.000837% | 0.00109% |

These errors apply to the specified fixture and excitation, without fitting or normalization. The weak 500–2000 Hz band has too little energy to establish general audible-band convergence. The source is generic, the contact transmission path is not measured KU100 construction, and the film reduction omits important wet-contact mechanisms. Passing the software checks does not establish the requested full recording realism.

## Reproduction and provenance

Use the commands in [README.md](../README.md). Tests invoke real native executables; measured-bank cases require `python scripts/prepare_ku100.py --download`. The workflow regenerates native examples from the checkout and retains its commit/source/binary identity in every bundle. Successful CI uploads its built viewer, generated bundles and evidence as a downloadable artifact.

Earlier independent audit snapshots intentionally retain the exact source/build hashes they tested. The final integrated suite includes the subsequent metadata-only addition of the global plate displacement bound to the CLI report. Physical equations and waveforms were unchanged by that serialization addition. See [research-audit-probe.json](research-audit-probe.json) for the refreshed scientific review identity.

The manually activated Pages workflow and a passing local build do not establish a live site. Record deployment success and the real GitHub-provided URL separately after first-time settings are configured.
