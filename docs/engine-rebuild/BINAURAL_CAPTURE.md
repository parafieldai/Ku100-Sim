# Binaural capture required for all object previews

30 September 2026. Replaces the dual-mono preview policy of the first shared
mechanical and measured-object demonstrations. User feedback: those objects did
not have the desired ASMR character; a recognizable source-only demonstration
was not the requested product. This change fixes their missing receiver path,
not the unresolved source-material/contact realism.

## One source engine and one microphone receiver

`SimulationEngine(scene).render_binaural()` runs the existing mechanical kernel
and sends its scalar source representation to `BinauralMicrophone`. The nine
measured object-tap variants use the SAME receiver class. There is no fork, plastic
or silicone-specific binaural algorithm and no duplicate-ear fallback.

The native receiver is `native/binaural/renderer.cpp`; it reuses the existing
`native/receiver.cpp` bank reader and fractional-delay construction. A scalar
internal source is not a mono listening output: it is passed through TWO distinct
measured impulse responses, preserving their time, level and spectral cues.
Public object WAVs must have two active, nonidentical channels. The validation
rejects duplicated mono and one-active-ear outputs, rather than trusting a stereo
file header. A zero-excitation numerical test stays exactly silent; no ambience
is inserted to make silence pass a publication test.

The previous public source-only/mono option on `/source/` is removed. Existing
reference-fitted ear-texture audio retains its existing stereo algorithm; it is
not falsely relabeled a newly calibrated microphone recording. `/unified/` and
`/objects/` are rerendered through the new shared capture path.

## What is measured, and what remains an approximation

The receiver uses the hash-pinned KU100 near-field bank already audited in this
repository: five horizontal circles, 360 azimuths each, two ears, 128 taps per ear.
The closest circle is 0.25 m from HEAD CENTER, NOT a 0.25 m ear gap and definitely
not an ear-touching measurement. The allowed radii are 0.25/0.50/0.75/1.0/1.5 m.
This component forbids intermediate-distance interpolation and extrapolation;
the previously measured distance-interpolation errors are not hidden.

The source is the authors' [near-field compilation](https://zenodo.org/records/4297951).
Attribution: Johannes M. Arend, Annika Neidhardt and Christoph Poerschmann. Embedded
SOFA notice: CC BY-SA 3.0; record metadata: CC BY 4.0. The original source-file
notice, attribution and share-alike condition are retained, without a relicensing
claim. See [data/manifest.json](../../data/manifest.json) and
[orientation-check.json](../../data/orientation-check.json). No user performance
waveforms are added to the repository or public site.

The actual capsule orientation is the verified named MIRO convention: channel 0
left, channel 1 right, 90 degrees left, 270/-90 right. Contradictory published
ReceiverPosition signs are not used to swap channels. Restored distance gains
are already in the bank and are applied ONCE. Another inverse-distance factor
would be wrong. The bank's approximately 200 Hz low-frequency extension is
analytical postprocessing, not independently measured low-frequency ear contact.

For the shared mechanics, the source signal is still an uncalibrated weighted
velocity readout with declared gain and band limiting. Treating it as a compact
point source is an acoustic approximation, not a completed source-radiation solve.
It lacks fork quadrupole directionality, resolved plastic-shell radiation and
identified silicone/interface noise. Binaural filtering cannot repair wrong
source timbre, dynamics or gesture behavior.

For the fitted wood/ceramic/glass responses, original recording/radiation/support
coloration remains mixed in the source coefficients. Applying the KU100 receiver
is an explicitly labeled TRANSPLANTATION of that colored source, not recovery of
an uncolored emitted field or verified reproduction of an object recorded by a
KU100. The manifest exposes this distinction in
`original_source_capture_coloration_retained`. We do not quietly call this
calibrated force-to-pressure physics.

The 3Dio Free Space and Pro II are not aliases for the KU100 bank. Their distinct
ear assembly and capsules require receiver-specific measurements; see the
[manufacturer](https://3diosound.com/products/free-space-pro-binaural-microphone).
The API rejects a 3Dio model request rather than returning mislabeled KU100 audio.
Direct artificial-ear contact, sealing and occlusion also require a different
identified path; a 1 cm source position is rejected here, not silently clamped.

## Stateful dynamic rendering

A scene's `microphone` field defines the device, a measured radius and azimuth
knots in seconds/degrees. The default six-second examples move slowly from near
right to near left through the front, with smooth starts/stops. This motion is
independent of the object's excitation and deformation; it represents moving the
source around a fixed microphone, not rotating a fork about its own stem.

The signal equation is a time-varying FIR:

```
y_e[n] = sum_k h_e(phi[n], r, k) x[n-k],   e = L,R
```

Each full filter combines the bank HRIR with ONE restored common propagation
fractional delay. Angular interpolation is linear between adjacent one-degree
responses, updated every audio sample. Quintic trajectory interpolation avoids
parameter jumps. Both ears use the same trajectory and gain; their differences
come from measured responses, not a pan law or stereo-widening delay.

At fixed position the result matches independently assembled full convolution.
At varying position this is a quasi-static receiver approximation, not a complete
moving-boundary wave solution. Constant head-center radius avoids changing common
range delay; source speed is restricted to 0.5 m/s and angular speed to 100 deg/s.
Propagation r/343 s and the fractional-delay implementation's 31-sample latency
are reported separately. Both full filter tails are retained; six-second input
at 0.25 m produces 288223 frames. Source path/state visualization subtracts that
known common delay but is not a calibrated capsule group-delay measurement.

[Arend et al., magnitude-corrected and time-aligned HRTF interpolation](https://arxiv.org/abs/2303.09966)
documents why sparse interpolation and contralateral responses need care. This
implementation uses the existing dense one-degree bank, not that paper's proposed
interpolator. It does not claim the paper's accuracy. The previously saved bank
validation remains separately versioned.

## Tests and user-visible behavior

The new receiver tests compare a separately decoded bank and NumPy/SciPy delay/FIR
reference to native output at fixed and moving positions. They cover actual ear
orientation, propagation/gain, angle wrapping, interpolation continuity, complete
tails, arbitrary block sizes, zero input, no file reads after initialization,
corrupt bank and unsupported device/contact rejection. `validate_binaural.py`
checks all 16 delivered object examples and records their nonidentical channels.

The original mechanical kernel is unchanged. A new optional microphone field does
not alter mechanical integration. Time refinement, no-recording source rendering
and energy tests remain applicable. Tests that previously REQUIRED identical ears
are explicitly replaced with the user's opposite output contract. Their physics
thresholds and codec/hash checks are not loosened.

Pages plays actual offline renders and exports edited scene JSON; it still does
not pretend to rerender when an editor field changes. The new microphone-path
editor affects the NEXT native render. Browser verification checks sample identity,
distinct ear signals, playback, seeking, downloads, and preservation of receiver
parameters in edited scenes.
The application never normalizes ears independently. Matched object pulse variants
share their gain; the very quiet smooth-contact scene is not inflated with noise.

Source-only numerical checks remain internal. Listening acceptance is explicitly
unassigned. The user's previous negative ASMR evaluation is not replaced by a
numerical pass or a claim that binaural processing guarantees tingles.

## Run

```
python scripts/prepare_ku100.py --download
python -m unittest tests.test_binaural -v
python scripts/render_unified.py scenes/unified/plastic-snap.json --out outputs/binaural-snap --gain 12
python scripts/build_object_examples.py
python scripts/build_unified_examples.py
python scripts/validate_binaural.py
python scripts/package_unified_site.py
node scripts/browser_objects.mjs
node scripts/browser_unified.mjs
```

Use fresh generated/output directories. The receiver loads only the verified
measurement bank. No source performance clip is replayed by either new renderer.
Actual runtime source models and measurement filters are separately identified
in each report, including hashes and approximation limits.
