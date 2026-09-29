# Independent audit of scientific claims

Audit date: 2026-09-29; refreshed against the **0.01 N default** and new operating-regime diagnostics. Scope: native source pressure, measured airborne receiver, amplitude reference, timing, low-frequency evidence, and the limits of the stated validation. No native source was changed for this audit. Source hashes and additional measurements are in [research-audit-probe.json](research-audit-probe.json); current numerical fixture validation is recorded in [physics-convergence.json](physics-convergence.json). The preliminary 0.6 N run is explicitly historical and failed the model's operating-regime screens.

**The implementation supports a numerically checked generic physical fixture and a reproducible measured KU100 airborne filter. It does not establish KU100 contact fidelity, absolute KU100 output level, or a fully calibrated source-to-capsule transfer.** The current `absolute_device_calibration:false` flag and the qualifications in [PHYSICS.md](../docs/PHYSICS.md) are appropriate. Numerical conservation, source provenance, and perceptual/device fidelity are separate questions.

## 1. Amplitude reference: dimensionally defensible, not an absolute calibration

At `native/physics.cpp:296`, the radiation branch uses

\[
R=\frac{\rho c}{4\pi a^2},\qquad \tau=\frac a c,\qquad
\tau\dot z=Q-z,\qquad p(a)=R(Q-z).
\]

Its transfer impedance is therefore

\[
\frac{p(a)}Q=\frac{\rho c}{4\pi a^2}\frac{s\tau}{1+s\tau}.
\]

This is the standard small-amplitude pulsating-sphere radiation impedance, with units Pa·s/m³. The core `airborne_pressure_*_at_025m_pa` observation multiplies by `a/0.25`, yielding pascals at a 0.25 m amplitude reference, before propagation time. Its low-frequency limit is `rho * dQ/dt / (4 pi * 0.25)`. The [MIT primary lecture notes, equations 3.23 and 3.29](https://ocw.mit.edu/courses/6-551j-acoustics-of-speech-and-hearing-fall-2004/7056ab51d5cb75810bf976ee38ac8f30_lec_3_2004.pdf) support that reduction. They do not establish that a real ear or vent has this radiation load.

The chosen source amplitude reference is **constant** while the receiver radius changes. The bank already contains the authors' restored relative distance factors, applied once in preparation. `native/receiver.cpp:168` correctly adds no second inverse-distance multiplier. An additional `0.25/r` would double-apply a distance envelope and introduce another −6.02 dB at 0.5 m, −12.04 dB at 1 m, and −15.56 dB at 1.5 m, relative to 0.25 m. The same warning applies if source pressure were first evaluated at the target radius and then passed through the corrected bank.

**Unresolved scientific requirement:** the author-corrected bank is not accompanied here by a verified absolute conversion from its normalized measurement amplitude to the model's pressure at 0.25 m. The [author correction note](https://zenodo.org/api/records/4297951/files/NF_Datasets_Gains_infos.pdf/content) restores relative natural level differences and warns that MIRO normalization omits changed preamplifier gains. It does not specify that a one-pascal input in this implementation gives one-pascal-calibrated capsule pressure. A dimensionless FIR can operate on a Pa-valued array without establishing this physical calibration.

For illustration, the actual prepared bank has the following frontal transfer magnitudes. These are measured coefficients, not errors or a justification for forcing unity gain:

| Radius | DC gain L/R | 1 kHz magnitude L/R |
| ---: | ---: | ---: |
| 0.25 m | 0.8023 /0.8175 | 0.6549 /0.6813 |
| 0.50 m | 0.3311 /0.3328 | 0.3172 /0.3301 |
| 0.75 m | 0.2487 /0.2519 | 0.2438 /0.2569 |
| 1.00 m | 0.1589 /0.1614 | 0.1667 /0.1762 |
| 1.50 m | 0.09544 /0.09499 | 0.09997 /0.10491 |

In `native/main.cpp`, the default nominal capture conversion is 20 mV/Pa ×10 preamp voltage gain ÷2 V full scale = **0.1 digital units per model pascal**. [Neumann's published 20 mV/Pa sensitivity](https://www.neumann.com/en-us/products/microphones/ku-100) is a hardware specification at 1 kHz, not a missing source-reference calibration. Applying it after an uncalibrated relative receiver does not establish an actual KU100 voltage or SPL. For the contact route, the separate unresolved step is model-chamber pressure → actual capsule pressure. The generic chamber has not been identified with that capsule.

The current metadata now explicitly describes this capture conversion as a nominal scalar and states that target capsule pressure is not calibrated. The airborne example separately declares **90 dB** of preamp gain, or **316.23 digital units per model pascal**, because its equivalent vent output is quiet. That transparent scalar affects audibility; it is not additional physical radiation, a measured amplifier model, or evidence of attainable hardware signal-to-noise. Microphone and electronics noise are not simulated.

**Required claim boundary:** retain the explicit nominal-conversion and device-calibration-false labels. Do not call the final WAV an absolute KU100 SPL prediction. Do not conceal the missing reference with a fitted per-ear gain, radius-dependent correction, or unity normalization. Closing this gap requires author-confirmed reference conventions and gain/sensitivity information, or a new source-pressure/capsule-voltage calibration with known geometry and recording gain.

## 2. Operating-regime correction and limited bandwidth

The [original TH Köln measurement paper](https://zenodo.org/api/records/4297951/files/Arend_TMT2016.pdf/content), section 2.2, applies adaptive low-frequency extension at 200 Hz, followed by source-response compensation and 128-tap retention. Thus the low-frequency portion is partly constructed by the authors' processing; it is not an independent physical contact measurement. The circular release avoids robot-arm effects, but the paper identifies head–loudspeaker reflections affecting the closest 0.25 m circular measurements.

The current native fixture uses a **0.01 N** nominal preload. In the 0.8 s default stroke probe, the conservative global plate-displacement bound is **0.06212 plate thicknesses**, peak vent Mach number is **0.00310**, and peak vent Reynolds number is **141.3**. The bound sums `|W_i q_i|`, so the unit-bounded spatial sine functions make it cover every point on both modeled plates. It passes the declared conservative screens: displacement bound/thickness ≤0.1, Mach ≤0.05 and Reynolds ≤1000. These are model-screening criteria, not universal transition boundaries or full-device validation. The global bound can conservatively flag a case whose actual spatial maximum is smaller; no waveform correction forces a pass.

The same current probe has raw chamber RMS pressures of **1.1008/0.7658 Pa**. Welch analysis of 0.12–0.55 s using 80 ms Hann windows gives:

| Quantity | Selected chamber | Opposite chamber |
| --- | ---: | ---: |
| Fraction of 20–4000 Hz power below 250 Hz | **88.6685%** | **30.8358%** |
| Fraction in 250–500 Hz | 11.3314% | 69.1642% |
| Fraction in 500–2000 Hz | 8.91 ×10⁻⁷ | 4.24 ×10⁻⁸ |

These are raw generic chamber measurements, before microphone gains or HRIR filtering, and exclude DC and power below 20 Hz. They are not KU100 measurements. Almost all assessed power is below 500 Hz. The current report's 250 Hz band must not be misquoted as a below-200 Hz measurement: an exact 200 Hz split has not been recomputed for the corrected default. The default 128-mode structural basis spans **20.77–1167.84 Hz**; output at 48 kHz does not imply a mechanically resolved 20 kHz model.

The same probe conserves its modeled work to about **1.59 ×10⁻¹⁸ J** against **1.069 ×10⁻⁴ J** of input work. Increasing 128→256 modes changes whole-waveform pressure by about **0.220%/0.127%**, while the very weak 500–2000 Hz PSD changes by **0.952%/0.869%**. These checks support numerical accounting and this trajectory's refinement behavior. The almost unexcited high band cannot substantiate broadband convergence or high-frequency rubbing realism. Matching or convolving the analytically extended HRTF cannot validate the contact source that produced these pressures.

**Historical invalid-regime result, not the current default:** the earlier 0.6 N run displaced the contact point by approximately 9.384 mm, or 3.128 plate thicknesses, and reached vent Mach 0.171/Reynolds 7784. Its previously reported 99.8784%/96.1378% below-200 Hz fractions belong only to that rejected operating point. Those historical arrays and hashes are segregated in the audit JSON. They must not be used as evidence for the corrected 0.01 N model. This correction itself demonstrates why a passing discrete energy balance is insufficient to validate the physical regime.

**Required claim boundary:** neither a tiny energy residual nor close whole-waveform agreement proves a realistic KU100 contact spectrum. Validation needs a physically meaningful excitation of the claimed frequency band and independent bilateral contact measurements, including force and motion. The mechanical model and the measured receiver must be assessed separately before any combined device claim.

## 3. Timing: useful modeled propagation, preserved relative cues, unknown absolute origin

The source bank's `Data.Delay` values are zero, but its time-domain responses contain nonzero latency. The authors compensated source phase/group delay and windowed the results. Zero `Data.Delay` is not evidence of zero acoustic or processing delay inside the arrays.

The implementation deliberately retains the complete arrays and adds one **common** modeled propagation term `r/c` in `render_airborne`. That preserves measured left/right relative timing. Both ears also receive the same causal fractional-delay interpolation. It is defensible for a declared auralization model whose absolute origin remains uncalibrated; it is not a reconstruction of the original measurement system's trigger-to-capsule timing.

| Timing component at default rates | Value | Interpretation |
| --- | ---: | --- |
| Decimation FIR | 64 output samples =1.3333 ms | Known processing delay for input rate >48 kHz |
| Fractional-delay FIR | Nominal 31 output samples =0.6458 ms | Known common interpolation latency, retained at integer delays |
| Added flight, 0.25 m /343 m/s | 0.7289 ms | Modeled head-centre propagation |
| Added flight, 1.50 m /343 m/s | 4.3732 ms | Modeled head-centre propagation |
| Bank frontal peak index | 29–31 samples =0.604–0.646 ms | Preserved measurement processing plus acoustic response, not a removable calibrated delay |
| Bank frontal 1 kHz group delay | Approximately 0.538–0.636 ms | Frequency-dependent; neither absolute flight time nor a common scalar |
| Source array first sample | t=1/192000 s =5.208 µs | End-of-step observation; time zero is not sampled |

The metadata separates the two known DSP delays from modeled flight, which is good. It now explicitly records the end-of-step first-sample origin in `simulation_first_sample_s`. It records that HRIR timing is preserved, but does not supply an absolute physical source-onset calibration. Consumers synchronizing a trace and an audio file must respect all of those fields. Do not subtract each ear's peak independently: that would destroy ITD.

For strict finite-sphere timing, a wave beginning at the sphere surface travels `(r-a)/c`; the implementation uses a point-equivalent centre convention `r/c`. The difference at the default 1 mm radius is 2.92 µs. This is small compared with the unresolved HRIR origin, but should not be described as exact finite-sphere trigger timing. The more consequential limitation remains the processed measurement origin and frequency-dependent transfer.

## 4. Measured filtering is not a contact equivalence test

[Bank validation](../data/validation.json) verifies all source coefficients, once-only gains, cardinal cues, and held-out interpolation. [Orientation validation](../data/orientation-check.json) resolves the SOFA position inconsistency through named original MIRO channels rather than inferring ears from loudness. These are strong implementation checks.

They also expose limits: removing a complete 0.5 m ring yields 6.49 dB median spectral interpolation error; corresponding 0.75 and 1 m errors are 2.41 and 1.33 dB. The held-out direction test instead has approximately 0.43–0.46 dB median error. Neither test certifies unmeasured fractional radii or positions at a contacting fingertip.

The [independent SADIE comparison](../data/sadie-benchmark.json) uses another real KU100 session, not coefficients read back from the same source. On 360 common horizontal directions at 1.2 m, after one common gain adjustment only, it leaves 2.72 dB median spectral RMS disagreement and 4.17 dB median frequency-dependent ILD RMS disagreement. SADIE's [original release](https://zenodo.org/records/12092466) and actual SOFA metadata specify their own low-frequency extension and diffuse-field equalization. Therefore the comparison is valuable evidence of spatial agreement and cross-session differences, not a clean measurement of the native source's physical error.

The code's bilateral contact path represents two plates/chambers connected by a declared air duct. No source inspected establishes this as KU100 internal anatomy, material, or transmission. The airborne mode observes only the selected vent as a relocated external source; it is not the total radiation of both plates, both vents, their supports, and a head shell. Its present description as a selected-vent observation is appropriately narrow.

**Release wording supported by the evidence:** “A native reduced physical model with measured KU100 airborne filtering, verified numerical work balance, explicit interpolation benchmarks, and uncalibrated device/contact transfer.”

**Claims not established:** “KU100 digital twin,” “realistic KU100 wet contact,” “measured 3Dio profile,” “calibrated capsule SPL,” “full-band structural accuracy,” or “proof of perceptual equivalence.” A generic physical model, a published dataset, and a passing numerical test suite together do not provide those missing measurements.

## Evidence and reproducibility

- [Source hashes and the new gain/timing/spectrum measurements](research-audit-probe.json).
- [Physics refinement and accounting report](physics-convergence.json), generated by `scripts/validate_physics.py`.
- [Bank provenance](../data/manifest.json), [data license discrepancy](../data/LICENSE_DATA.md), [preparation and roundtrip](../scripts/prepare_ku100.py).
- [Original gain correction](https://zenodo.org/api/records/4297951/files/NF_Datasets_Gains_infos.pdf/content), [original near-field paper](https://zenodo.org/api/records/4297951/files/Arend_TMT2016.pdf/content), [author dataset](https://zenodo.org/records/4297951).
- [Neumann KU100 official specification](https://www.neumann.com/en-us/products/microphones/ku-100), [MIT spherical-wave/radiation notes](https://ocw.mit.edu/courses/6-551j-acoustics-of-speech-and-hearing-fall-2004/7056ab51d5cb75810bf976ee38ac8f30_lec_3_2004.pdf), [SADIE original release](https://zenodo.org/records/12092466).

The bank probe computes `H(f)=sum h[n] exp(-j2πfn/fs)` directly, DC as the coefficient sum, and group delay as `Re(sum n h[n] exp(-j2πfn/fs)/H(f))/fs`. Current physics quantities are taken from the source-hashed authoritative `physics-convergence.json`, whose trajectory records the corrected 0.01 N load. The older exact below-200 Hz split used unchanged double-precision arrays from the 0.6 N run; its raw-array hash and invalid-regime status are retained only inside the historical section of the audit JSON. No historical spectrum is presented as a current-default measurement.
