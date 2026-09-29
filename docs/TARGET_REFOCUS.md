# Target-first source investigation — 29 September 2026

## Acceptance contract, not a renamed plate demo

The original September 11 research brief and September 25 handoff specify **nonverbal tongue–saliva contact with an artificial outer ear**, including slide, rolling, hold, peel and release. Motion, loading, wetness and history must influence fresh generated sound. Recorded performances may inform research and comparisons, never supply runtime clips. The user rejected the plate/chamber examples as unlike this target. Those examples are preserved as engineering tests, not accepted target sounds.

The brief also explicitly requires distinguishing direct ear contact from mouth-internal sound radiated toward the microphones before selecting a source model. The supplied video-derived reference has an avatar, not measured contact motion. The four available ear-labeled WAVs provide acoustic observations but no synchronized force or identified action. Their hardware and recording processing are unverified. No pop is labeled a bubble collapse by sound alone.

## This update's bounded experiment

**Question:** can release of stored air pressure produce a source component worth comparing with short target transients? This is a competing *airborne source* hypothesis. It is not a tongue/ear, saliva, adhesive peeling or liquid-bridge solver.

The new native source generates an air-pocket pressure/flow trajectory, then passes its equivalent free-field source through the already verified KU100 receiver bank **at the measured 0.25 m radius**. It does not extend that measurement to millimetre contact. The old direct plate output is not mixed in. Neither target WAV samples, fitted target spectra, random noise nor captured transient fragments enter synthesis.

Four variants share the same source schedule and constants: 1 ms opening on the left, 20 ms opening on the left, a never-sealed control, and the 1 ms source on the right. They are source-discrimination probes, not four validated ASMR triggers. Seal/opening and wall motion are prescribed inputs; fluid pressure, neck flow, viscous memory and radiation evolve continuously. No state resets are inserted between events.

The public comparison is `target.html`, linked prominently above the engineering fixtures. It accepts local reference WAVs without uploading them, preserves their stereo order, offers exact original generated WAV exports and records blank-by-default listening judgments with file identities. The original rejected baseline is selectable. One scalar per stereo clip can be used for capped digital RMS audition; original unscaled measurements and exports remain unchanged. This is not calibrated loudness matching. The never-sealed control should also be compared with matching **off**, because amplification can conceal its small physical amplitude.

## Equations and declared approximation

Let p be air-pocket excess pressure [Pa], Q neck volume flow [m³/s], u the prescribed extra pocket volume [m³], and z the radiation memory [m³/s]. Pocket compliance is C = V/(rho c²). The implementation solves:

```
C dp/dt = -Q - du/dt
neck_impedance(Q) + R_seal(t) Q + K(t) |Q|Q + R_rad (Q-z) = p
(tau dz/dt) = Q-z
R_seal = 8 eta seal_length / (pi opening_radius^4)
K = rho / (2 Cd² (pi opening_radius²)²)
R_rad = rho c / (4 pi neck_radius²)
tau = neck_radius / c
p_source_at_0.25m = (neck_radius / 0.25) R_rad (Q-z)
```

The fixed neck uses the existing positive-memory viscous impedance. A separate short, prescribed **resistive** opening supplies the seal. Its variation has no moving inertance or elastic-energy store. This simplification is intentional: it is **not** a complete moving-aperture fluid solution, and neglects time-dependent reactive aperture/end-correction effects. Opening actuation/structural sound is not modeled. The empirical entrance-loss coefficient is an assumption, not target calibration.

Every midpoint step solves the nonlinear flow magnitude analytically and accounts for `-p_mid Delta u` work, compliance and viscous/radiation stored energy, and nonnegative viscous, resistive, quadratic and radiation losses. Loss terms act inside the pressure/flow dynamics, not in an output equalizer. No state is rescaled to close the energy budget.

Default assumed constants: V=0.8 mL, neck radius=1.2 mm, fixed neck length=2 mm, seal length=0.1 mm, leakage radius=10 micrometres, wall-volume change=0.7 microlitres, period=0.9 s, air density=1.204 kg/m³, sound speed=343 m/s, dynamic viscosity=1.81e-5 Pa s, discharge coefficient=0.7. They define an exploratory bench apparatus, **not measured oral geometry**. One full-scale digital unit per Pa is a declared observation gain, not calibrated microphone electronics. Source code and measured-bank hashes accompany each generated study.

The prescribed cycle is seal, pocket expansion, hold, open, and wall return. The code uses smooth transitions and retains state during gaps. There is no asserted mapping from these times to a real tongue action. Full wet-contact mechanisms, dynamically identified controls and an anatomical visual simulation remain absent.

## Numerical audit: failed settings retained

`validate_release.py` assembles an independent continuous 3×3 reference with a matrix exponential for the constant-open, **linear legacy-viscosity subcase**, initially 80 Pa, evaluated at 2 ms. This is not an independent solution for the full nonlinear memory model.

| Integration rate | Energy-weighted final-state error | 0.5% criterion |
|---|---:|---|
| 192 kHz | 2.219635% | fail |
| 384 kHz | 0.555326% | fail |
| **768 kHz** | **0.138857%** | pass |

The initial 384 kHz assertion failed. The criterion was not relaxed: the production probe now uses 768 kHz. For the specified two-second nonlinear, unsteady release, direct 384→768 kHz source-waveform difference is **0.368845%**, with no fitted phase, delay or gain. This is finite-case temporal evidence, not a spatially converged oral-fluid model or a perceptual threshold.

At 768 kHz the two-second sealed source has peak pocket pressure about 122.15 Pa, peak aperture Mach 0.02631 and Reynolds 343.36. The never-sealed source RMS is **0.0001392 times** the sealed result. No wall-volume movement produces exact silence. Work/energy, opening ablation, deterministic replay and continuous-reference checks are automated. These calculations test the assumed source—not its relevance to the target.

## Actual target comparison: a narrow negative result

Fixed previously inspected four-second diagnostics are chapter 03 at 57–61 s, chapter 04 at 90–94 s, chapter 05 at 65–69 s and chapter 06 at 51–55 s. They are deliberately **not called held-out data**, controlled actions or an identification set. Full-file hashes and sample-exact crop indices are in [the reference summary](../web/target-reference-summary.json). They are not the six-second or whole-file intervals used in earlier reports.

A declared 40–18,000 Hz envelope detector finds 6.25, 5.25, 8.75 and 2.75 peaks/second in these four cuts. Their relative activity is approximately 26.25%, 30.39%, 39.02% and 11.03%. The source's fast-opening example has about **1 peak/second and 1.40% activity**. Its sparse prescribed bursts therefore do **not** explain the references' sustained activity and event density. This is a rejection of the current probe as a complete source model, not evidence that pressure releases never contribute. Detector peaks are not identified tongue actions, and weak controls' relative peaks are not audibility claims.

The four reference signed L−R RMS differences are approximately **−33.79, +11.98, −40.20 and +36.82 dB**. The fast airborne source is about **+19.09 dB** on the left and −19.06 dB on the right. Geometry, source placement and processing differ; no physical equivalence is inferred from a closer number. No arbitrary per-ear leakage factor was fitted.

The generated fast/slow variants redistribute spectral power strongly, but **a brighter transient is not a wet texture**. This release-only source does not generate continuous sliding, rolling, filament breakup or wet-contact memory. The app keeps `physical_target_accepted=false`, `listener_assessment=null` and `source_mechanism_identified_in_target=false`.

## What counts as useful listening feedback

First compare the target and source audio without the optional source-state plot. Judge a short attack/decay component separately from continuous wet texture and left/right presentation. Record “mismatch” when applicable; no rating is inferred from workflow success. Match level for a timbre question, then turn matching off to inspect each control's original output level. Save the review JSON; it contains the candidate, source hashes, reference crop, matching gain and unfilled or explicitly selected judgments. It is not transmitted by the site.

The current source fails the **complete-target** requirement on observable activity/coverage alone. A matching attack would justify investigating that component—not accepting the model. If attacks also mismatch, do not retain the component just because its equations conserve energy. Next identification must distinguish tongue/surface friction, mouth-internal contact/pressure release and actual wet-interface dynamics. A short repeated dry-versus-wet, ear-contact-versus-no-ear-contact comparison is more informative than adding unrelated SFX presets. No request to buy equipment or capture data has been sent.

## Reproduction and access

```
python scripts/prepare_ku100.py --download
python scripts/build_release.py
build/ku100-release --out outputs/new-release --opening 0.001 --azimuth 90
python scripts/validate_release.py
python scripts/generate_examples.py
python scripts/build_site.py
python scripts/package_preview.py --out outputs/review
```

CI packages `outputs/review/target.html` without reference audio. `package_target.py --references LOCAL_DIRECTORY --out PRIVATE_FILE.html` explicitly makes a local comparison with the four supplied excerpts; it refuses destinations in `web/` or `dist/`. That private file is for the user and is never an input to public publication. No raw reference recording, reference clip, frame-level waveform or sensor trace is committed.

Primary-source inventory, publication boundaries and later SFX lanes are in [SFX_TRIGGER_RESEARCH.md](SFX_TRIGGER_RESEARCH.md). Stored local findings are in [release-validation.json](../validation/targets/release-validation.json); the current CI regenerates its own receipts and source hashes. Automated playback is not human listening. No new subagent or participant study is claimed.
