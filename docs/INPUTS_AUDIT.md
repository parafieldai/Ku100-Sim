# Uploaded archives, documents and reference audio

## Source recovery result

The four supplied ZIPs were intact. The latest recovered fresh-audio generator was **Hybrid 09**, a fitted mono procedural generator. The later Target Audio Checkpoint supplied stereo analysis and reconstruction of existing performances. It did not supply a new contact-force-driven generator. No implementation of the newer README's advertised coupled Mindlin/contact/cavity/radiation JavaScript engine was found in the supplied archives.

The native code in this repository is a new implementation based on the documented physical equations and independent checks. It does not present missing earlier code or historical README measurements as newly reproduced evidence.

| Input ZIP | Compressed bytes | Outer members | Integrity |
| --- | ---: | ---: | --- |
| Parafield-01-Site-and-Handoff.zip | 270,078,041 | 180 | Full member reads and CRC passed |
| Parafield-02-Releases-and-Results.zip | 351,868,597 | 63 | Full member reads and CRC passed |
| Parafield-03-Original-Inputs.zip | 271,940,729 | 4 | Full member reads and CRC passed |
| Parafield-Target-Audio-Checkpoint.zip | 194,233,346 | 127 | Full member reads and CRC passed |

The handoff checksum manifest passed **246/246** size and SHA-256 comparisons; the target checkpoint passed **126/126**. All **10 nested ZIPs** also passed full CRC reads. Five nested release manifests passed **353/353** comparisons: Audio Lab 83, Fidelity 73, Realism Research 4, Alternatives 80 and Hybrid 09 113. [The compact integrity record](../validation/input-archive-integrity.json) retains archive hashes, member counts and manifest results.

Archive code was read and audited; extraction did not execute archive-supplied scripts. Large user recordings and previous release blobs are not runtime dependencies or published website files.

## What the recovered implementations do

| Recovered component | Finding and implication |
| --- | --- |
| Hybrid 09 `src/hybrid.py` and `src/evaluation.py` | Fitted sustained spectra, stochastic/LPC transients and authored controls; mono generation/evaluation. Its separate two-coordinate physical identification fixture is not coupled to production sound. |
| Hybrid 09 `src/physical.py` | A useful numerical parameter-identification example; explicitly does not identify a tongue, ear, liquid, radiation or microphone. |
| Alternatives `src/cavity.py` | Passive two-state pressure/flow cavity advanced by a matrix exponential, with illustrative geometry. No contact, elastic plate or reciprocal radiation-loaded source. |
| Earlier browser `site/src/v6/engine.mjs` | Fitted stochastic acoustic states. The receiver has 128-tap KU100 responses at 0.25 m and seven selected azimuths. It is not a calibrated contact model. |
| Original `wet-physics-v3/engine.mjs` | Approximate contact and squeeze-film state with heuristic bridge/bubble births and random resonator excitation; not the later advertised Mindlin solver. |
| Original `ku100_renderer.cpp` copies | Steam Audio propagation wrappers that consume source recordings; they do not generate contact sound from new forces. |
| Target `reference-audit/analyze_references.py` | Complete-file stereo digital-level, spectrum, temporal and channel diagnostics; exact input hashes retained. |
| Target `representation/run_representation_experiment.py` | Reconstruction and ablation of the same recorded timeline. The checkpoint explicitly states no new-action generation or physical training. High reconstruction SNR does not establish fresh-synthesis realism. |

The recovered geometry described as an IHA scan is a **human** scan, not a KU100 scan. It was not relabeled or imported into the new viewer. The current visual geometry is an original generic fixture illustration.

## Comparison with the supplied references

Five user-supplied stereo 44.1 kHz, 16-bit WAVs total **929 seconds**. Their filenames and export metadata do **not** establish microphone model, original source URL, force history, gain settings, calibration or equivalence to an earlier selected YouTube source. Those fields remain unverified.

The following whole-file measurements come from the verified target audit. Positive L−R means the left channel has more RMS energy. Correlation is mean-removed zero-lag sample Pearson correlation, not a binaural realism measure.

| Reference | Duration | L−R RMS | Correlation | L power <250 Hz | R power <250 Hz |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chapter 02, mixed | 382 s | +0.761 dB | 0.00766 | 97.00% | 95.49% |
| Chapter 03, right label | 120 s | −34.809 dB | 0.22621 | 68.34% | 87.69% |
| Chapter 04, left label | 184 s | +24.436 dB | 0.06801 | 92.83% | 87.07% |
| Chapter 05, right label | 134 s | −28.506 dB | 0.10775 | 63.62% | 94.59% |
| Chapter 06, left label | 109 s | +37.502 dB | 0.30774 | 93.00% | 15.30% |

The current native demonstrations produce the following results. Their complete scenes and hashes are in [examples.json](../validation/examples.json).

| Native example | L−R RMS | Correlation | L power <250 Hz | R power <250 Hz |
| --- | ---: | ---: | ---: | ---: |
| Dry left stroke | +3.476 dB | 0.18943 | 96.78% | 94.11% |
| Viscous-film left stroke | +3.160 dB | 0.24849 | 89.16% | 83.66% |
| Right tap | −4.829 dB | −0.30733 | 99.98% | 99.99% |
| Left press/release | +2.975 dB | 0.27329 | 100.00% | 99.99% |
| Airborne vent through KU100 bank | +5.381 dB | 0.99258 | 99.97% | 99.97% |

The native contact examples have **2.97–4.83 dB** absolute whole-file channel imbalance, versus **24.44–37.50 dB** in the four ear-labeled recordings. This is an observable mismatch. A common capture/listening gain cannot fix it, and no per-ear leakage coefficient was fitted to hide it. Matching a single low-frequency power percentage would also not establish the correct mechanism or realistic sound.

The power comparison uses the reference audit's Hann 8192-sample Welch windows, 4096-sample hop, per-window constant detrending and final partial-window zero padding. Native outputs are resampled from 48 to 44.1 kHz **for analysis only**, giving the same frequency grid and window duration. Original exports remain unchanged. The recordings last 109–382 seconds; native examples last approximately 2–4 seconds and have different gestures. Their onset/release balance differs, so these descriptive percentages cannot be treated as controlled paired trials. The separate physical convergence report deliberately measures a steady interval and therefore has different band fractions.

Reproduce the summary from the original target audit and freshly generated native examples:

```sh
python scripts/compare_references.py --reference-audit PATH_TO_reference_audit.json
```

[reference-comparison.json](../validation/reference-comparison.json) records the source-audit hash, individual recording hashes, native audio/source hashes, method and full numerical rows. Original performances are not included in this repository and are never used during rendering.

## What would establish device fidelity

A usable validation set must identify the exact microphone and capsule revision, geometry/materials, gain and filtering, force and motion, dry/wet conditions and both channels. Fit the physical model on one subset, then test held-out loads, positions and gestures. Measure force-to-vibration and force-to-pressure magnitude/phase, decay and bilateral transfer. Follow objective checks with controlled human listening.

The current software and archive checks establish integrity and numerical behavior. They leave the requested KU100/3Dio contact realism unproven and expose concrete differences that still need physical explanation.
