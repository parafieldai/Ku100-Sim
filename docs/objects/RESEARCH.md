# Distinct object sounds: data-assisted simulation experiment

## What was tested

Three named RealImpact objects: `27_WoodPlate`, `64_CeramicMug`, and
`94_GlassGoblet`. The implemented action is tapping/impact. This is not a test of
brushes, crumpling, liquids, or wet-ear mechanics, and not a general SFX engine.
The existing native solver and the ear-reference texture models are unchanged.

An initial small, unmeasured oscillator prior did not reproduce these objects'
measured spectra. We therefore identified reduced-order modal responses from real
measurements. This prior is an illustrative baseline, NOT a full finite-element
simulation or the RealImpact paper's state-of-the-art comparison.

## Real data actually inspected

[RealImpact](https://samuelpclarke.com/realimpact/), Clarke et al., CVPR 2023,
records controlled impacts at known object and microphone positions. The
[paper, sections 4.1 and 4.4](https://arxiv.org/html/2306.09944v1) gives the 48 kHz
sampling rate and describes correcting microphone signals using the measured
hammer force. The authors' [preprocessor](https://github.com/samuel-clarke/RealImpact/blob/main/preprocess_measurements.py)
explains the released `deconvolved_0db.npy` signal and gain processing.

We extracted original array rows **7, 22, 37, 52** from each of the three published
object ZIPs: 12 mono responses, not the entire 150,000-recording dataset. Their
microphone coordinates are `(0.23,-0.04345,0)`, `(0.563,-0.04345,0)`,
`(0.896,-0.04345,0)`, `(1.23,-0.04345,0)` metres. The radial labels 0.23/0.56/0.90/
1.23 m follow the gantry convention, not exact source-to-microphone distances.
They are **not binaural ears**. Each object subset contains only one impact vertex,
one azimuth and one microphone height, at four distances and different strikes.

These ZIPs contain corrected microphone responses and geometry metadata, not the
raw force and raw microphone arrays referenced by the preprocessing program.
Consequently we cannot independently undo/revalidate their force correction or
claim absolute N-to-Pa calibration. Their numeric amplitudes are not playable
normalized PCM until explicitly scaled. The source is also not KU100 audio.

Acquisition uses bounded byte ranges and decodes only selected initial NPY rows,
without pickle or executing dataset code. The [receipt](../../validation/objects/data-receipt.json)
records object/member names, shapes, selected rows, byte-range hashes and local
subset hashes. The full remote archive/member CRC is NOT verified because only
prefixes were acquired. The downloaded Actions artifact's complete ZIP CRC and
SHA-256 were verified. The first acquisition found metadata only because expected
raw member names were absent; the corrected run acquired `deconvolved_0db.npy`.
Future acquisition fails if any requested audio is unavailable, while retaining
its failure receipt.

No source recording is a runtime sound asset or Pages file. The authors' software
license was inspected, but we do not infer that every recording's redistribution
rights are identical to the code license. Attribution is retained in profiles and
this document. Generated demonstrations, not source recordings, are published.

## Model: a compact dynamical response, not a sound clip

For each object, 24 decaying oscillators are fit to **row 7 only**, after the same
80 Hz high-pass, declared onset detector, 1.5 s crop and one peak scaling. A greedy
variable-projection search fits frequency and decay; a joint linear solve obtains
two output coefficients per oscillator. This is an original small implementation,
not ESPRIT or an implementation of the authors' fitter.

The impulse response of mode k is

```
h_k(t) = exp(-d_k t) [C_k cos(w_k t) + S_k sin(w_k t)]
q_k'' + 2 d_k q_k' + (w_k^2 + d_k^2) q_k = u(t)
y_k = (w_k S_k + d_k C_k) q_k + C_k q_k'
```

For a unit impulse with `q(0)=0, q'(0)=1`, the second expression gives the first.
The runtime uses a stable two-pole recurrence with radius `exp(-d_k/fs)`.
Positive damping produces nonincreasing free mechanical-state energy; it does not
prove the fitted microphone output is in Pa or that a stochastic residual is a
passive physical contact mechanism.

The model retains frequency, decay, and **two phase-bearing modal residues**. It
does not retain a PCM waveform, a measured impulse-response buffer, a recording
residual, or a performance timeline. Unlike the earlier phase-free stationary
texture model, phase is represented parametrically here; it must not be described
as the same method or as containing no phase information.

Wood and glass required a generated transient layer after the modal-only fit left
large broadband errors. This layer retains only 16 band-power mixtures of four
fixed amplitude-decay rates (8, 32, 128, 512 /s), plus a scalar. Runtime draws new
seeded noise and filters/modulates it using those parameters. Late measurement
noise is subtracted in the variance fit. This is a statistical approximation of
unexplained transient structure, **not identified friction or contact mechanics**.
For ceramic, the extra layer worsened the training spectral comparison and was
rejected. Selection uses the training comparison only.

Published examples prescribe new impact times and relative impulses; each impulse
has a unit-discrete-area half-sine pulse. Pulse width changes source excitation,
not playback speed. Nominal widths 40/130 microseconds round to 2/6 samples at
48 kHz. Those are experiments, not identified actual hammer or finger materials.
Model identification includes unseparated mounting, radiation and capture effects;
there is no independently identified geometry/material/position transfer solver.

## Primary research informing this choice

- [Clarke et al., RealImpact (2023)](https://arxiv.org/html/2306.09944v1): modal
  response and spatial transfer are separate; measured sound fields expose a
  substantial simulation-to-reality gap. Supports the dataset choice, not our
  numerical thresholds or perceptual acceptance.
- [Sterling et al., Audio-Material Reconstruction (2019)](https://pubmed.ncbi.nlm.nih.gov/30762560/):
  uses real recordings to constrain damping while addressing confounds. Our
  fitter does not implement their probabilistic damping model.
- [Aramaki & Kronland-Martinet, Analysis-Synthesis of Impact Sounds (2006)](https://kronland.fr/publications/analysis-synthesis-of-impact-sounds-by-real-time-dynamic-filtering/):
  supports investigating deterministic plus stochastic impact structure. Our
  16-band transient approximation is not a reproduction or a validation of their
  model, and its sound remains to be judged.

## Test split and actual result

Row 7 was used for parameter estimation. Rows 22, 37 and 52 were compared after
freezing each candidate. These rows were already inspected during the modal-only
prototype, so this is a **development distance-transfer assessment**, not newly
blind validation. It checks whether one fixed response retains similar normalized
timbre at other measured positions; it does not predict the spatial sound field.

[Full assessment](../../validation/objects/assessment.json) and
[initial modal-only results](../../validation/objects/initial-modal-only.json)
retain failures. Spectrum is compared in 1/12-octave bands between approximately
100 Hz and 16 kHz after level normalization, excluding reference bands below
0.01% of evaluated energy. The other diagnostic is normalized integrated-energy
rise/decay error. Median results use three fresh noise seeds. The deliberately
bounded engineering screen is <=6 dB spectral RMS discrepancy and <=0.15 energy-
decay RMS discrepancy. Neither threshold has been established as an ASMR or
perceptual-realism threshold.

| Object | Fitted position spectral error | 0.56 m | 0.90 m | 1.23 m |
|---|---:|---:|---:|---:|
| Wood plate | 2.82 dB | 4.76 dB | 3.61 dB | 4.87 dB |
| Ceramic mug | 3.23 dB | 5.91 dB | 4.99 dB | **8.41 dB: fails** |
| Glass goblet | 2.26 dB | 4.09 dB | 4.87 dB | **12.29 dB: fails** |

Seven of nine non-fitting position cases meet both diagnostic limits. The two
failures remain failures. Normalized comparisons do not establish level accuracy,
airborne pressure, absolute contact force, other impact points, other items,
perceptual identity, or a convincing KU100/3Dio recording.

## Playback and reproducibility

`/objects/` offers each item with shorter and longer contact pulses, plus its
unmeasured prior as a diagnostic. The fitted variants use identical impact times,
relative impulse strengths, random seeds and one shared gain per object. A longer
pulse can therefore be quieter; no per-variant normalization hides that change.
Priors have their own stated listening gain. A 10 ms end fade avoids cutting a
prior's decay. The underlying numerical assessment uses unfaded model responses.

The recordings are **not replayed**. After reading bounded parameter JSON files,
the renderer is tested with file opens and NumPy array loads blocked. Generated
output is 48 kHz PCM16, dual mono to isolate timbre—not spatial ASMR. PCM16 is a
preview storage decision, not the internal solver precision (float64). The
previous native Float32 publication contract and all existing audio remain intact.

```bash
python scripts/acquire_impact_subset.py  # private/local research measurements
python scripts/fit_object_models.py --data validation/local/impact-data \
  --out models/new-object-profiles --report validation/local/object-assessment.json
python -m unittest tests.test_modal_object tests.test_object_publication -v
python scripts/build_object_examples.py  # uses checked-in parameter-only profiles
# After the normal main/texture/long generation prerequisites:
python scripts/package_object_site.py
node scripts/browser_objects.mjs
```

Model/output directories must be new. Source-array hashes, rows, preprocessing,
model hashes and complete diagnostics are retained. No unrelated ear reference
is used. A human listening assessment and broader recording comparisons remain
necessary; successful playback cannot be reported as successful realism.
