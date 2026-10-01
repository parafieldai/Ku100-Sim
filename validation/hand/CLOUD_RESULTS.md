# Connected fingertip–pad scene: executed pre-integration evidence

Research date: 30 September 2026 (Pacific time). Cloud execution finished 1 October UTC. This is a measurement-informed mechanical prototype, not an ASMR listening acceptance or a calibrated ear-pressure model.

## Actual executed work

[Branch run 36798172207](https://github.com/parafieldai/Ku100-Sim/actions/runs/36798172207) completed successfully, including the full 236 Python/native tests, 25 frontend tests, four new five-second hand/contact renders, four 1.5-second refinement diagnostics, seven preserved fork configurations, and the HTTP browser suites. Native/Python tests took 45.108 seconds on the cloud runner. The separate local full-suite run passed the same 236 tests in 59.569 seconds.

The branch artifact is `hand-contact-validation-36798172207`, ID `11134907588`, 37,143,570 bytes, SHA-256:

```
9717f0a38d56b03547f501f5f22b9ee9230221c1d7118dfb514ed78bfedf8b63
```

The artifact was downloaded. Its full hash and every ZIP CRC passed. All 42 changed files in its expanded source matched local byte counts, SHA-256 values and Git blob IDs. The indexed, tested tree was `174f16196616c9c4731ca92a4beee50c922a72d9`. Its native finite-strain source SHA-256 is `74f3a964245bf42af7e685b1d1cb523c5d42ab1762c22ed2c2499f40fdd1af5b`.

Before main integration, the inspected screenshot exposed a clipped thumb label and narrow numeric columns. Two presentation-only files, `web/hand/app.js` and `web/hand/style.css`, were adjusted to keep the label and force values readable. Their final main browser run must be checked separately. Those changes do not touch mechanics, scene data, audio generation, material fitting, numerical thresholds or audio bytes. The remaining 40 files use the exact branch-tested blobs. The material-acquisition workflow and this receipt are also preserved; temporary transport blobs/workflow are excluded from the main tree.

## Real material data, not source recordings

[Material acquisition 36794174982](https://github.com/parafieldai/Ku100-Sim/actions/runs/36794174982) downloaded the published compression ZIP without executing dataset code. Artifact 11132727018 is 90,167 bytes and has SHA-256 `fa068c17502bbbe8c6d9a660143e6a850f9c8f14709a1044c1c144e845d4d1d6`; the artifact was independently downloaded and every CRC passed. The original compression ZIP SHA-256 is `7acde7e17883150264a528a55bced8d1828c8f70179066df81ad4f6545c5b856`, matching the fitted model's provenance.

The five Ecoflex 00-30 curves were inspected. An ideal homogeneous incompressible compression formula was fitted to replicates 1–3 over 5–20% nominal compression. The effective shear modulus is 52,596.06185 Pa. Relative stress residuals are 2.663%, 4.611% and 4.381%; development replicates 4 and 5 give 4.865% and 6.751%. Re-running the fit from the source ZIP reproduces the checked-in JSON byte for byte. This is not the paper's full Ogden/inverse-FE procedure, a multiaxial validation, an audio-band loss measurement, or measured fingertip friction.

Raw material CSVs and user sound recordings are not publication assets. The stored model contains fitted parameters, data hashes, scope and errors. No sound recording or learned audio texture is read to synthesize the four new contact examples.

## Numerical results include explicit failures

The initial element-volume formulation and its poor mesh/source comparisons remain in `initial/`. An energy-derived averaged-nodal-volume formulation reduced the default-to-finer source-flux discrepancy from approximately 53.97% to 41.56%, but did not make it converged.

| Diagnostic, first 1.5 seconds | Observed relative L2 | Declared limit | Result |
|---|---:|---:|---|
| Force, 96 to 192 kHz | 0.000639% / 0.000599% | 1% | Pass |
| Force, default to finer mesh | 5.1683% / 5.0263% | 5% | **Fail** |
| Surface-flux source, default to finer mesh | 41.5601% | 5% | **Fail** |

No fitting gain or waveform alignment was used. The temporal source-flux difference is approximately 0.4329%. These diagnostics stop partway through rubbing, not after the full five-second gesture. `validate_hand_scene.py` can complete and retain these failures: its completion is not a spatial-accuracy pass. Source timbre, held-out recording accuracy and pressure-like perception have no acceptance verdict. No numerical threshold was relaxed to produce a green workflow.

The lighter contact has approximately 0.348/0.329 N peak reactions. The stronger stress case reaches approximately 2.054/1.701 N, but compresses the assumed linear fingertip layer by about 75.5% of its thickness. It is not qualified as a realistic hand-contact force experiment. The light scene is the default; even its skin/friction/receiver assumptions remain unvalidated. The shown load in N is not a microphone-pressure value or a haptic guarantee.

## Rendering and browser evidence

All four new contact WAVs match the corresponding local renders byte for byte. All seven fork WAVs match the exact prior `Ku100-Fork-Radiation-Results.zip` auditions preferred by the user. This checks the actual bytes, not only unchanged parameters.

Chromium 151.0.7922.34 checked 45 combined hand/fork site assets, all four contact and seven fork audio examples, distinct ear samples, actual playback, completed seeking, original downloads and scene export. The hand tests also check that the displayed force and deforming surface correspond to saved native state at the chosen time. Desktop/mobile ordinary HTTP project-subpath navigation succeeded without app errors or reference uploads. The old shared-engine browser suite also passed. A browser playback check is not a human listening assessment.

The local runtime's normal browser navigation was blocked by policy; it was not bypassed. The successful HTTP claims here come from the cloud run and its downloaded evidence, not a local in-memory substitute.

A separate local instrumented build of the new C++ source passed all 22 solid-scene tests under AddressSanitizer and UndefinedBehaviorSanitizer. GNU C++ 14.2.0 used `-O1 -g -fPIC -shared -fsanitize=address,undefined -fno-omit-frame-pointer`; halt-on-error was enabled and leak detection disabled. This covers those tests, not exhaustive memory safety or the acoustic model.

## Scope

One public `SimulationEngine` composes the geometric solid/contact backend and shared binaural capture. The pad has 140 connected vertices and 432 tetrahedra; two translating compliant fingertip proxies receive equal/opposite contact forces. This is not a full anatomical/articulated hand. There is no arbitrary mesh loader, water, air pocket, self-contact, adhesive peel or wet seal model in this implementation. Surface radiation is a six-group approximation at a measured KU100 airborne ring, not a calibrated hand-on-ear field.

The near-field fork experiment remains separately scoped: compact-source radiation with spherical-head near-field prediction anchored by measured KU100 data. No new measured 3 cm microphone response is claimed.

No human listening result or new LLM-subagent audit is claimed. Main CI, actual Pages deployment and anonymous live-site verification must be checked after integration. Earlier statistical generators are still regenerated by full main CI; their exact historical WAV bytes must not be assumed preserved.

See [HAND_CONTACT.md](../../docs/engine-rebuild/HAND_CONTACT.md), [FORK_NEAR_FIELD.md](../../docs/engine-rebuild/FORK_NEAR_FIELD.md), and [the material fit](../../models/materials/ecoflex-compression.json).
