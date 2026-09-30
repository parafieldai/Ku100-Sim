# Source texture iteration — 29 September local / 30 September 2026 UTC

## User feedback and the target

The user says the previous sounds are convincingly near the ear and recognizable as ear picking, but do not have the character of the ASMR SFX in the supplied recordings. This is a timbre/texture failure, not evidence of insufficient spatial width or of a listener's inability to experience tingles. No sensory judgment has been assigned to the new examples.

This iteration addresses the handoff's analysis/synthesis representation step. **It does not replace the requested physical simulator with a claim that acoustic statistics are contact physics.** The native C++ mechanics, pressure-release probe and original generated examples are unchanged. The new path is offline microphone-domain waveform synthesis and the `/source/` listening page.

## What actually changes

The old empirical source uses a hardcoded 1,500/s renewal impulse process and averages event-life spectral shapes after normalizing individual events. Matching that average can produce a common scratch-like texture, overweight quiet bright events, and discard dependencies between frequency bands and time. That mechanism is a code-derived explanation to test, not a diagnosis from an asserted private listening session.

The new model stores three-scale aggregate spectral and envelope descriptors: spectral power; compressed-envelope mean, dispersion, skew and kurtosis; lagged cross-band products; separate rising/falling envelope variation; and absolute waveform moments. FFT sizes are 256, 1,024 and 4,096 at 48 kHz. The bands are log-spaced triangles, **not a claimed physiological cochlear model**. Lags are 0, 1, 2, 4, 8 and 16 analysis hops.

Rendering starts from fresh seeded noise and optimizes a waveform against those statistics. The optimizer works in whitened waveform coordinates; a fixed training-derived spectral shaper conditions the optimization. There is no imposed pulse clock, no stored source phase, no reference event sequence, and no recorded grain lookup. The objective is computed from realizable waveforms, rather than independently specifying an inconsistent spectrogram and claiming a phase reconstruction has succeeded.

The waveform is still stochastic acoustic synthesis. The code does not identify saliva breakup, force, wetness, peeling, mouth anatomy or pressure in pascals. Rendering is offline and noncausal, not interactive physical control. A matched spectrum by itself is not the objective or acceptance test.

## Fitting populations: do not merge these claims

| Published item | Fitting data | Correct interpretation |
|---|---|---|
| Revised source / right | Chapter 03, 57–63 s, near channel right | Same-excerpt texture-representation test; **not held-out prediction** |
| Revised source / left | Chapter 04, 89–95 s, near channel left | Same-excerpt texture-representation test; **not held-out prediction** |
| Range-fitted source / right | Chapter 03, 0–50 and 70–120 s | Excludes the displayed center excerpt, but that excerpt was previously inspected; not a new blind validation |
| Previous burst sources | Frozen existing burst models | Historical acoustic baselines, reprojected through the common shaper for this panel only |
| Spectrum-matched controls | Revised GENERATED waveform, with its phases randomized | A structure ablation, not another object or gesture |

Reference hardware, physical action, force and recording processing are unverified. The source hash and exact fitting ranges are recorded inside each aggregate model. Reference audio is resampled to 48 kHz and high-passed at 35 Hz for fitting, continuously within each range. One global fitting normalization is used; individual quiet events are not raised to the same level as loud ones.

The compact `.ctm.xz` files contain **float16 aggregate parameters**, not source audio. Optimization uses float32. On the three published models the maximum log-power quantization error is below 0.04 dB; that is a parameter-storage bound, not an output-audio fidelity score. Expansion and shapes are bounded and all decoded values are checked. The reproduction fitter supports the same format. No original reference audio, event list, or time-dependent spectral sequence is stored in these files.

## Isolating texture from spatial presentation

For each side the old burst fit supplies one fixed minimum-phase inter-ear log-magnitude ratio. All new, previous and control sources in this panel pass through that same frozen filter. No new spatial parameters are fitted. **This is a controlled comparison path, not a statement that every older stereo waveform is reproduced, or that the filter is anatomically calibrated.** Overall inter-ear level can depend on a changed source spectrum even through a fixed filter.

The page's “Source only” mode sends the actual dominant/source channel equally to both ears, for the candidate and an imported reference. It does not change playback speed, regenerate the sound, or alter original downloaded WAVs.

The spectrum-matched control preserves the revised generated source's complete Fourier magnitudes to floating-point tolerance **before** the shared 10 ms file fade. It disrupts temporal structure without deliberately changing spectral balance. The boundary fade and finite-window spectral measurement can introduce small measured differences afterward. The original procedural burst remains a separate baseline; the comparison does not conceal it by equalizing it into the new source.

Playback files use one declared scalar per stereo clip to target near-channel 35-Hz-high-passed RMS 0.04, with a static 0.6 peak cap. The high-pass is used for the gain measurement, not as an output equalizer. A shared 10 ms file fade avoids cut-edge discontinuities. This is not calibrated microphone loudness or perceptual loudness matching. The UI starts at −6 dB headphone attenuation; start with a low device volume.

## Executed development, including less successful attempts

1. Direct waveform-coordinate optimization of the 100 s right range fit reduced its aggregate objective from about 78.9 to 15.7. Small-amplitude spectral components were poorly conditioned.
2. Whitened-coordinate optimization of the same fitted statistics reached about 0.078 after 800 iterations. This is a change in optimization, not an “ASMR improvement percentage.”
3. Constraining all individual Fourier magnitudes at initialization reached about 13.5. This was not selected as the default renderer. The stronger diagnostic instead randomizes the **final generated** spectrum after synthesis.
4. Explicit reference-guided models are then evaluated separately from the broader range fit. They address representational fidelity on the requested passages without pretending that this is unseen-action prediction.

The full-precision development render's near-ear 1–4 kHz power fraction for the right excerpt was about 0.564%, versus 0.589% in the reference and 25.347% in the previous burst source. The left revised source was about 0.514%, versus 0.527% in the reference. These are development spectral descriptors, not an acceptance verdict. The new right acoustic detector rate still differed from the reference (about 4.15 versus 2.83 peaks/s). The final compact-model CI render supplies its own current numbers in `validation/local/source-iteration.json` and `source/generated/iteration.json`.

There is no fitted time alignment and no waveform-SNR “realism” score. Matching these same-excerpt descriptors cannot establish a correct sound-producing mechanism. Repeated user audition and an actual listening assessment remain necessary.

## Sources and their scope

- McDermott & Simoncelli (2011), *Sound Texture Perception via Statistics of the Auditory Periphery*, DOI [10.1016/j.neuron.2011.06.032](https://doi.org/10.1016/j.neuron.2011.06.032), [primary abstract](https://pubmed.ncbi.nlm.nih.gov/21903084/). Supports testing correlations across auditory channels in addition to marginal power/sparsity. Their sound-texture results do **not** validate these target recordings or this implementation.
- Caracalla & Roebel (2019), *Sound texture synthesis using convolutional neural networks*, [author manuscript](https://arxiv.org/abs/1905.03637). Supports investigating temporal cross-correlations and waveform-domain optimization instead of a separate harmful phase-recovery stage. This implementation does not use their CNN and is not described as a reproduction.
- Shier et al. (2023), *Differentiable Modeling of Percussive Audio with Transient and Spectral Synthesis*, [author project](https://jordieshier.com/projects/differentiable_transient_synthesis/). Supports treating transient detail as a separate modeling concern; its instrument results are not wet-contact evidence.

These sources informed a bounded source-representation experiment. They do not replace the target-system mechanics and paired-data requirements of the original handoff.

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-texture.txt
python -m unittest tests.test_texture_source -v
python scripts/build_texture_iteration.py
python scripts/assess_texture_iteration.py
# Existing full site prerequisites still apply:
python scripts/build_site.py
node scripts/browser_source.mjs
```

Fresh fitting requires the user's original recordings locally, not in GitHub:

```bash
python scripts/fit_texture_source.py --input CHAPTER_03.wav --side right --reference --out right-reference.ctm.xz
python scripts/fit_texture_source.py --input CHAPTER_04.wav --side left --reference --out left-reference.ctm.xz
```

Without `--reference`, the fitter uses the disjoint ranges declared above. Existing model/output files are never silently overwritten. Test artifacts and histories should always retain the actual source/model hashes, not be relabeled after a source change.

## Publication and remaining work

`/source/` presents stable names and immediate generated-audio playback. The older `/target/` now uses named auditions by default, with randomized identities available only through its explicit blind-mode checkbox. Original reference WAVs remain browser-local and are not published. Numerical/shape/privacy tests and actual browser playback checks run separately from listening acceptance; the post-deployment workflow also checks the real HTTPS page.

This is an acoustic source iteration. It has no newly validated tongue/ear contact law, no physical gesture controller, no proof of a true microphone transfer, and no prefilled human score. The new output should be judged against the stated SFX character before selecting a source representation to connect to physical state.
