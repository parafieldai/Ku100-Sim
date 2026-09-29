# Main-renderer quality investigation

## Separate three different problems

The previous 8x free-decay error and 6x6/12x12 structural discrepancy belong to `benchmarks/contact-coupon`, not to the main Mindlin/duct renderer. They remain in that benchmark's historical evidence; their thresholds have not been weakened and their results are not assigned to this engine.

Numerical time-step error is addressed with a reference solution or controlled time refinement. Modal error requires a fixed geometry and fixed forcing footprint with a nested basis. Neither issue requires more ASMR recordings to expose or correct the implementation error. Device-specific physical fidelity, however, additionally needs geometry, constitutive measurements and matched contact-to-microphone evidence.

The main driver originally contained wavelengths from 3 mm to 120 micrometres. At the default 0.035 m/s speed, its highest advected texture frequency is about 291.7 Hz. Integration at 192 kHz does not add missing high-frequency excitation. Transients/nonlinearities can generate additional frequencies, so this number is not a hard output cutoff.

## Implemented changes

- Passive frequency-dependent viscous tube memory, with reciprocal source loading and complete energy accounting. See [VISCOUS_LOSSES.md](VISCOUS_LOSSES.md).
- Explicit minimum/maximum texture wavelengths and amplitude exponent, validated in the native CLI, Python scene contract and browser. Undersampled texture advection is rejected. The old parameters remain defaults for reproducibility.
- Per-ear, per-band comparison that refuses to call an unexcited band converged. A 0.5% L2 target is applied independently to each assessed ear/band. Bands below 0.001% of the reference's 20–20000 Hz power are marked **unassessed**, not passed. These are engineering screens, not psychoacoustic thresholds.
- Separate sub-20-Hz/DC pressure statistics from 20–20000 Hz spectral fractions. Historical all-frequency measurements remain present but are not silently reinterpreted as audible-band results.
- Seven real native examples and a self-contained offline viewer, with original WAV exports. The browser explicitly shows texture-advection bandwidth, highest retained mode and loss-model choice.

## Two new examples

`unsteady-stroke-left.json` changes the air-loss model and uses 256 modes per plate. Its source texture, nominal load and capture gain remain unchanged. The stricter assessment found that 128 versus 256 modes can miss the 0.5% band-error target even though the whole-waveform difference is small. The 256/512 comparison meets the target in the sufficiently excited low bands for the declared probe.

`fine-texture-left.json` uses 10-micrometre minimum texture wavelength and 512 modes. It is a **microgeometry sensitivity experiment**, not measured tongue texture and not a fidelity improvement claim. Changing the wavelength range changes the texture realization; it is not a mesh-refinement comparison. It still fails to establish full-band target sound. No high-frequency noise, sample fragments or corrective equalization are added to conceal the mismatch.

## Reproduce

```sh
python -m pip install -r requirements.txt
python scripts/build_native.py
python scripts/prepare_ku100.py --download
python -m unittest discover -s tests -v
python scripts/validate_viscous.py
python scripts/quality_gate.py
python scripts/generate_examples.py
python scripts/package_preview.py --out outputs/review
```

The quality assessment executes eleven native trajectories, including silence, true mirrored excitation, modal refinements and temporal refinements. Its report can complete successfully while `full_band_contact_fidelity_established` remains false. A green software workflow is not a green realism certificate.

## Capture and perception remain separate

The physical cavity pressure is not established as KU100 capsule pressure. The nominal electronics do not model the microphone's complete frequency response or self-noise. Neumann documents linear, 40 Hz and 150 Hz low-cut positions affecting both channels; see [manufacturer specifications](https://www.neumann.com/en-in/products/microphones/ku-100). We do not assume which setting was used in the user's recordings, invent an exact transfer function from cutoff labels, or apply an undisclosed low cut to improve a score.

A real validation capture should retain raw stereo; identify the microphone/revision and all capture processing; synchronize position, normal/tangential force and a bandwidth-qualified vibration measurement; and include held-out strokes, releases and wetness conditions. Force logging rate alone is not sensor bandwidth. A useful minimum experimental design varies a small number of speeds and loads, repeats dry and controlled-fluid contacts, and preserves full release events. Its numerical ranges must be chosen for the actual fixture's safe, measurable regime rather than copied from this generic model.

No human listening assessment has been performed by these scripts. Listener judgments should be recorded separately for timbre, action correspondence, stereo realism and ASMR response, using the exact rendered file hashes. Perceptual ratings must not be filled in by a software test.
