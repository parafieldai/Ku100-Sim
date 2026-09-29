> Historical report preserved from the delivered `Ku100-Research-Update.md`. Figures refer to its named commits and runs, not to later changes. Only this banner and the historical CI heading were added.

# KU100 main-renderer research and implementation update

Application development continues in `native/`, `scripts/`, `ku100sim/`, and `web/`. The separate contact-coupon benchmark is unchanged. The new component is a bounded generic physical model, not a calibrated wet-contact digital twin.

## Historical main-branch CI at 27f6851

The final main commit `27f685172a19ab5cd8829da93195e91a01f6b09b` passed GitHub Actions run https://github.com/parafieldai/Ku100-Sim/actions/runs/36617778812 . Its artifact `ku100-verified-27f685172a19ab5cd8829da93195e91a01f6b09b` has SHA-256 `c6199581e4933c867468c0c689caf946df8d8061fcf65bcc2498f4d2170a527d`. All final preview member hashes were checked, and all seven WAVs are byte-identical to the initial successful implementation run. The required-band regression guard also passed.

The publication availability workflow ran at https://github.com/parafieldai/Ku100-Sim/actions/runs/36618108584 . Its deploy job was skipped because Pages was unavailable/unconfigured. A successful availability check is not a successful site deployment.

## Source and execution receipts

- Main implementation commit: `40cc3f12dfb41b24cbb9a90ee5268939de132851`.
- Publication and recurring preview CI: `b83ae11d9b71474b62cbeefbd3020cc91ba42b98`.
- Required-band regression guard: `27f685172a19ab5cd8829da93195e91a01f6b09b`.
- Verified cloud run for the implementation: https://github.com/parafieldai/Ku100-Sim/actions/runs/36616716883 .
- Cloud artifact: `main-quality-preview-36616716883`, SHA-256 `28626669724e46e7bbd4a53e49e795801ea4a15c5e0ae14ca39e4ee3a1f76762`. Its downloaded ZIP CRCs and preview member SHA-256 values were checked locally.

## What changed

Added positive-memory, frequency-dependent viscous circular-tube impedance to the main coupled structural/acoustic solver. Stored energy and loss include the memory states. This is not an output equalizer and does not add sampled or random high-frequency sound. The old loss model remains available for controlled comparisons. Thermal admittance, free surfaces, liquid bridges, cavitation, bubble formation and adhesive peeling are not implemented.

Added explicit spatial texture wavelengths and a sampling guard. At 0.035 m/s the original 120 micrometre shortest wavelength yields a highest advected texture component of 291.7 Hz. The 10 micrometre sensitivity example reaches 3500 Hz before the physical transfer. This is an unmeasured microgeometry experiment, not a calibrated tongue texture. Transients and nonlinearities can generate other frequencies.

Added per-ear/per-band numerical qualification, preserving failures and marking bands with less than 0.001% of the reference 20-20000 Hz power as unassessed. Whole-waveform differences and band errors are computed without fitted gain or delay. The shipped-preset guard requires the declared 20-500 Hz comparisons to pass; it does not establish full-band or perceptual fidelity.

## Analytical component validation

Maximum complex impedance relative error: 0.015646%. Maximum resistance relative error: 0.342124%. The test uses 1001 frequencies from 20 Hz to 20 kHz at four radii (0.5, 1, 3 and 10 mm) against an independently evaluated Bessel-function solution. These are bounded component checks, not microphone-equivalence measurements.

## Native refinement results

The following whole-waveform errors are from eleven 0.8-second native trajectories. Frequency-band checks use the fixed 0.12-0.55 second Hann window.

| Coarse case | Refined case | Left L2 error | Right L2 error |
|---|---|---:|---:|
| viscous128 | viscous256 | 0.206122% | 0.111765% |
| viscous256 | viscous512 | 0.032353% | 0.024467% |
| fine256 | fine512 | 0.031850% | 0.021590% |
| fine512 | fine1024 | 0.006194% | 0.007492% |
| viscous128 | viscous128-r384 | 0.005140% | 0.005808% |
| fine512 | fine512-r384 | 0.005413% | 0.006068% |

The 128/256 unsteady-loss comparison fails the 0.5% target in sufficiently excited bands (including about 0.834% left and 1.123% right in 250-500 Hz). The 256/512 comparison is about 0.236%/0.327% in that band and passes both 20-250 and 250-500 Hz. This motivated 256 modes for the new standard unsteady-loss example. Higher unexcited bands remain unassessed. The fine-texture example still does not establish a convincing upper-band output.

Mirror maximum pressure error in the probe: 6.03961e-14 Pa. Every probe passed its stated energy and physical-regime checks. These finite trajectories are not universal stability or constitutive-validity proof.

## Actual rendered examples

All seven examples are actual 48 kHz stereo Float32 native exports. A declared common capture gain is applied to both ears; there is no per-ear normalization or limiter. Browser listening attenuation does not alter the exported WAV. Start with low headphone volume.

| Example | Left RMS dBFS | Right RMS dBFS | Samples beyond full scale | Regime screen |
|---|---:|---:|---:|---|
| stroke-left | -25.554 | -29.030 | 0 | pass |
| wet-stroke-left | -25.230 | -28.390 | 0 | pass |
| tap-right | -26.941 | -22.112 | 0 | pass |
| airborne-left | -51.019 | -56.401 | 0 | pass |
| press-left | -26.336 | -29.311 | 0 | pass |
| unsteady-stroke-left | -25.297 | -28.989 | 0 | pass |
| fine-texture-left | -25.456 | -29.066 | 0 | pass |

Digital level is not a listening-quality score. Separate sub-20-Hz pressure motion from audible-band power: the old main dry-stroke example has approximately 91.4%/96.0% of total power below 20 Hz. New measurements retain that distinction instead of silently interpreting all pressure energy as audible sound. No actual capture low-cut setting is inferred for the user recordings.

## Dataset evidence

Hugging Face: four dataset cards and revision identifiers were inspected. OOPPEENN/ASMR_Dataset explicitly removes saliva sounds and separates channels, making it inappropriate as a direct wet-contact stereo target. Other inspected cards are speech/transcript-oriented or processed archives and do not establish paired force/motion/KU100 data. No HF audio was trained on or used at runtime.

Kaggle: the public ASMR search API was queried and its result JSON retained. The inspected YouTube ASMR channels entry is channel analytics, not synchronized contact recordings. This bounded search is not a claim that all Kaggle datasets were exhaustively searched.

Figshare/Cluster Haptic Texture Dataset: one matched raw/processed audio, force, acceleration and position trial was retrieved through bounded HTTP ranges from the full release. The entire 15.2 GB archive was not downloaded. The inspected trial is `0_0_20_1000_0` (nominal 20 mm/s, 1 N), 216395 audio frames at 44.1 kHz (4.9069 seconds), 42500 force/acceleration log rows, and 493 position rows. Per-member CRC and SHA-256 checks are preserved. Raw audio channel 0 is contact plus machine noise and channel 1 is the machine reference: they are not binaural ears.

The raw contact channel has 97.46% of its measured 20-20000 Hz power below 250 Hz; processed mono has 1.38%. Processed high-frequency dominance cannot be blindly attributed to contact physics. Force log row rate is not sensor bandwidth: adjacent repeated values and the paper’s 80 Hz converter description require explicit treatment. This trial was audited, not used to fit KU100 coefficients.

Primary data attribution: Michikuni Eguchi, Tomohiro Hayase, Yuichi Hiroi and Takefumi Hiraki; Cluster Haptic Texture Dataset, DOI 10.6084/m9.figshare.29438288.v5, CC BY 4.0. Only a derived summary is committed; raw trial assets are excluded from the public preview.

## Browser and implementation verification

Cloud implementation run: 69 native/Python tests, 17 frontend tests, original 15-scenario probe, new 11-trajectory quality assessment, analytical tube validation, 9 HTTP end-to-end browser groups, and 6 offline-browser checks. Browser: Chromium 151.0.7922.34. Automated checks verified exact stereo decoding, original WAV download hashes, playback progression, import/corruption rejection, scene editing, project-subpath hosting, mobile layout and no external requests from the offline preview. No human listening assessment or fresh subagent audit was performed.

## Availability

Open `Ku100-Research-Preview.html` in a browser; it embeds all seven actual native exports and needs no server. Original WAVs are available separately. The GitHub Actions artifact retains both preview and detailed measurements. Main CI is configured to regenerate these results for future commits and retain each artifact for 14 days.

The Pages API returned HTTP 404 during the verified implementation run. No live website is claimed. The new workflow supports the authorized public site and deploys only the exact successful main CI artifact when Pages is configured with GitHub Actions as the publishing source. It does not make the private repository or user reference recordings public.

## Remaining work before a realism claim

The numerical errors in the isolated coupon benchmark are not inherited main-renderer results. More ASMR data is not needed to identify integration or modal truncation errors. The wet-contact realism gap, however, requires identifying the relevant physical sources and measuring matched motion/load/vibration/raw stereo on the target device or a specified surrogate. Device geometry, viscoelasticity, wet adhesion and contact/capsule transmission remain uncalibrated. A high-precision receiver convolution cannot validate these missing links.

Next physical identification should use repeated controlled conditions and truly held-out actions/sessions; it should compare actual sounds and per-ear spectra without arbitrary leakage or high-frequency noise compensation. Keep human judgments of timbre, action correspondence, spatial realism and ASMR response separate from software pass/fail.

## Primary external sources

- Cluster data descriptor: https://www.nature.com/articles/s41597-026-06760-z .
- Cluster release: https://doi.org/10.6084/m9.figshare.29438288.v5 .
- Bilbao and Harrison, passive tube models: https://pubmed.ncbi.nlm.nih.gov/27475194/ .
- Source-card exclusion: https://huggingface.co/datasets/OOPPEENN/ASMR_Dataset .
- Manufacturer capture information: https://www.neumann.com/en-in/products/microphones/ku-100 .
- Measured airborne KU100 data: https://zenodo.org/records/4297951 .
- Pages permissions: https://docs.github.com/en/rest/pages/pages .

Implementation-derived claims above are supported by the accompanying JSON reports, source hashes and executed-test logs. External sources justify methods or identify data; they do not certify this simulator’s perceived realism.
