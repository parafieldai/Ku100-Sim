# Deformable contact and preserved fork: final main/live verification

Application commit: `9019b3f7c01b7d68914b93acef50c61e7a56ddbb`. Verified 30 September 2026 Pacific time; the GitHub runs are timestamped 1 October UTC.

## Actual deployment

- [Main CI 36799416399](https://github.com/parafieldai/Ku100-Sim/actions/runs/36799416399): completed successfully, including the full regression suite, original/new renders, diagnostics and all browser steps.
- [Pages publication 36801319302](https://github.com/parafieldai/Ku100-Sim/actions/runs/36801319302): prepare and actual deploy jobs succeeded.
- [Live verification 36801367221](https://github.com/parafieldai/Ku100-Sim/actions/runs/36801367221): all original and new public-HTTPS browser steps succeeded.

The actual live pages are:

- https://parafieldai.github.io/Ku100-Sim/hand/
- https://parafieldai.github.io/Ku100-Sim/fork-radiation/

The first is a research prototype with explicit numerical/source failures, not an accepted ASMR sound. The second publishes the exact previous fork auditions the user preferred; it is not a new retuning or a new near-ear measurement.

## Independent artifact verification

Both archives were downloaded. Full SHA-256 values matched GitHub's declared digests and every ZIP CRC passed.

| Artifact | ID | Bytes | SHA-256 |
|---|---:|---:|---|
| Main | 11135407854 | 144906294 | `a5ae614a695d08b08fc9eb384d3efb53c2fe3f84dcfde8503a163833728ebf4c` |
| Live | 11136381386 | 7147425 | `6e1f6f7d9813888626da5e64a7a90a609ac2999ed9e136a5476c6ef6974f725f` |

All four hand WAVs match the branch-tested output byte for byte. All seven fork WAVs match both the branch output and the original user-preferred `Ku100-Fork-Radiation-Results.zip` files byte for byte. Every scene, physical trace and report referenced by the hand manifest also matches its hash. All eleven WAVs are finite, 48 kHz Float32 stereo with two active, nonidentical channels and no samples at or beyond full scale.

The final live contact/fork report records **45 assets and 11 audio examples** checked by Chromium 151.0.7922.34. Every asset's reported live hash was independently compared with the actual downloaded main archive, not just with the report's own expected field. All returned HTTP 200. Playback, completed seeking, exact decoded samples, original downloads and scene export passed. The hand viewer consumes the hash-verified native geometry/force trace and its force readout/animation were exercised. No claim is made that the browser test independently recomputes the mechanics or quantitatively compares every screen pixel or force sample.

Both live hand screenshots were inspected: the thumb label is no longer clipped, and force values are readable in the desktop/mobile metric layout. The same tests cover ordinary HTTP project-subpath hosting. There were no reported application errors or uploaded references. Local normal browser navigation was blocked by administrator policy and was not bypassed; the ordinary HTTP/live results here come from the GitHub-hosted browser.

## Scope of verification

The full implementation regression suite contains **236 Python/native tests and 25 frontend tests**, all passing. The final main job reran the complete suite. The earlier branch run and separate local runs are documented in [CLOUD_RESULTS.md](CLOUD_RESULTS.md). A separate local ASan/UBSan build passed the 22 solid-scene tests; leak detection was disabled. Those 22 are not additional independent acoustic acceptance tests.

No numerical or listening threshold was weakened to obtain a green workflow. `validate_hand_scene.py` records failed spatial criteria while checking numerical integrity and temporal behavior; successful execution is NOT a spatial-accuracy pass.

## Important failures remain visible

The bounded 1.5-second stronger-contact development probe gives default-to-finer-mesh force differences of approximately **5.17% / 5.03%** and **41.56% surface-volume-flux difference**, against declared 5% mesh criteria. All three fail. The temporal force comparison is approximately **0.00064% / 0.00060%**, but that does not establish spatial or acoustic convergence. The shortened trajectory is reinterpolated and must not be described as literally the first 1.5 seconds of the five-second audition.

The default light-contact preview has peak reactions of approximately 0.348 / 0.329 N. The stronger scene reaches about 2.054 / 1.701 N while compressing the assumed linear fingertip layer by about 75% of its thickness. That stronger case is not qualified as a realistic physiological skin experiment. Computed contact load in newtons is not pressure at the listener's ear or a haptic guarantee.

Material behavior is informed by an actually acquired and hash-checked Ecoflex 00-30 compression release. The fitted effective shear modulus is 52,596.06185 Pa; the fit is limited to the stated uniaxial range and is not the source paper's full multiaxial inverse-FE procedure. Friction, fingertip behavior, audio-band loss and sound radiation remain uncalibrated. Raw measurement CSVs and performance recordings are not included in the website.

## Additional contact-integration research

After the production implementation, a separate static analytical test isolated false force modulation on a perfectly smooth plane caused by sparse contact quadrature. On the default grid and light indentation, the deployed three-point rule has about **18.72% spurious peak-to-peak force variation**. A forty-eight-point scratch rule reduces this to **0.366%**. No physical texture, friction, inertia or audio is present in that analytical experiment.

Six further local light-contact runs tested three quadrature rules on two meshes. Denser quadrature reduced source-flux mesh discrepancy from about **112.95% to 50.08%**, but every variant still fails the declared 5% criteria. Force convergence is not monotonic. This diagnoses one numerical problem; it does not prove a complete explanation of the unwanted sound or a finished fix. The denser variants are NOT deployed.

The reproduction script, derivation and full reports are now preserved under [research/contact-quadrature](../../research/contact-quadrature/README.md). It operates on temporary source copies, checks the production kernel is unchanged and uses no recordings. This research is separate from the cloud regression count. Its addition and this receipt use `[skip ci]`; neither changes the production solver, scene, material, audio, viewer or workflow.

## What remains outside this delivery

The same public `SimulationEngine` now composes a reusable finite-geometry solid/contact backend. It is not a bespoke renderer selected by the object's name. The pad is connected, and two compliant translating fingertip proxies receive reaction forces. It is not a full anatomical or articulated hand. There is no water, air pocket, wet seal, adhesive peel, self-contact or calibrated hand-on-KU100 pressure in this stage.

The six-patch surface radiation and measured KU100 airborne receiver are approximations. Fork near-field audio remains an ideal-sphere prediction anchored by measured receiver data, not a new measured three-centimetre ear response. No raw performance clip, arbitrary background sound or bass oscillator is inserted into these examples.

No human listening acceptance or newly spawned LLM-subagent audit is claimed. The user's requested pressure-like ASMR character remains unestablished. Preserve that distinction from engineering execution and actual website deployment. Older statistical audio is rerendered by full main CI; byte preservation is only claimed here for the four new contact and seven specifically checked fork files.

See [HAND_CONTACT.md](../../docs/engine-rebuild/HAND_CONTACT.md), [FORK_NEAR_FIELD.md](../../docs/engine-rebuild/FORK_NEAR_FIELD.md), and [the material fit](../../models/materials/ecoflex-compression.json).
