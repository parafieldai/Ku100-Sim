# Variations, duration and microphone pressure

This note separates the implemented acoustic source from published microphone
facts and a proposed physical contact model. It does not call statistical
waveform synthesis full tongue/saliva/KU100 physics.

## Was the reference audio edited?

During fitting, the source recordings are read, a selected channel is resampled
and high-passed, and its aggregate descriptors are measured. The stored texture
model contains average spectral powers, envelope moments, lagged cross-band
products and attack/release statistics. It does not contain the recorded waveform,
phase, chronological envelope track or individual sound grains.

During synthesis, the adjustable variable is a freshly seeded waveform. The
optimizer changes that new waveform until its aggregate statistics approximate
the fitted values. It never starts with the recorded waveform and modifies it.
The accurate name is reference-fitted statistical resynthesis. This is neither
sample editing nor a recording-independent physics solver. Same-excerpt fits
remain representation experiments, not held-out predictions or anti-memorization
certificates. See [SOURCE_ITERATION.md](SOURCE_ITERATION.md).

## Longer and varied output implemented in this iteration

`build_long_examples.py` generates three fresh 12-second right-channel sources
(seeds 5101/5102/5103) and one left source (5104), using the existing six-second
reference-fitted parameter files and 800 optimization steps. It exports right A,
right B and left A individually. The three right generations also form a 30-second
example with 3-second equal-power overlaps and starts at 0, 9 and 18 seconds.
Thus the long example contains the short A/B sources; those are not independent
comparison conditions. Nothing is looped or time-stretched, but overlapping
independent textures is not continuously simulated action/state. Joins can blend
or interrupt individual events. The stereo shaper's 1,023-sample tail adds about
21 ms to each nominal duration.

All output files use the existing frozen inter-ear filter for their side and
one shared gain for both ears. This preserves the source-comparison approach; it
does not calibrate absolute pressure or solve changing physical contact.
Read attempts on audio-file extensions are rejected during the generation
process. Input/model/code hashes, seeds, objective histories, gains, lengths and
output hashes accompany the WAVs. The public page includes generated files only.

Longer assemblies are technically possible, but should not be advertised as
minutes of coherent new gestures until transition behavior, repetition and
long-range structure have been tested. These four examples are a bounded
12/30-second demonstration, not proof of that broader claim.

## Published microphone facts

The [Neumann KU100](https://www.neumann.com/en-us/products/microphones/ku-100)
contains two omnidirectional condenser capsules in artificial ears on a head
housing. Its sensitivity is specified as 20 mV/Pa at 1 kHz into 1 kohm. Its outputs
are analog XLR/BNC. The published low-cut choices are linear, 40 Hz and 150 Hz;
the -10 dB pad and low-cut affect both channels.

The current [3Dio Free Space Pro II](https://3diosound.com/products/free-space-pro-binaural-microphone)
page names DPA 4060 CORE+ capsules and specifies nominal 20 mV/Pa at 1 kHz,
with silicone outer ears. It provides two analog XLR outputs and a stereo
3.5 mm output. Its 160 Hz bass roll-off applies to the 3.5 mm output only.
The model and capsule revision must be logged: color alone is not a device ID.
These source pages establish capture specifications, not local wet-contact
mechanics or the cause of any particular ASMR sensation.

[Neumann's condenser explanation](https://www.neumann.com/en-us/knowledge-base/neumann-im-homestudio/homestudio-academy/what-is-a-condenser-microphone)
explains the transduction: air pressure moves a thin diaphragm relative to a
backplate; capacitance changes and internal electronics buffer the resulting
signal. It is not an AI sound classifier. A microphone does not identify the
applied finger force or label a waveform as ASMR.

[DPA's pressure microphone definition](https://www.dpamicrophones.com/dict/pressure-microphone/)
and [equalization-vent explanation](https://www.dpamicrophones.com/dictionary/l/lf-equalizing-tubevent/)
are particularly important here. A pressure microphone has an equalization path
that rejects static ambient pressure and extremely low-frequency changes. A
steady external load is not therefore a permanent audio/DC value. Changes in
pressure can be recorded within the microphone's operating bandwidth. A hand
seal outside an artificial ear is not the same thing as the capsule's own
pressure-equalization vent.

[DPA also distinguishes proximity effect](https://www.dpamicrophones.com/mic-university/background-knowledge/proximity-effect-in-microphones-explained/):
the classic pressure-gradient bass boost does not occur in single pressure
omnidirectional capsules. Near-ear bass/contact/occlusion effects should not be
explained simply as the proximity effect of a cardioid microphone.

## Pressure -> electrical signal -> digital samples

The relevant paths are:

```
contact / airborne source / changed seal
    -> local acoustic pressure and possible structure-borne excitation
    -> diaphragm/capsule response
    -> analog microphone voltage (sensitivity and frequency response)
    -> preamp gain, input coupling and filters
    -> analog anti-alias filtering / ADC conversion and digital decimation
    -> stereo PCM samples in a recording file
```

[Analog Devices' DSP introduction](https://www.analog.com/en/resources/analog-dialogue/articles/dsp-101-part-1.html)
describes transduction, sampling and pre-ADC band limiting. Its
[anti-aliasing application note](https://www.analog.com/en/resources/technical-articles/antialiasing-basics-using-switchcapacitor-filters.html)
explains why aliased components cannot simply be removed afterward. Actual audio
interfaces can combine microphone preamps and converters, as described by
[Focusrite's OctoPre](https://focusrite.com/products/scarlett-octopre).

For a simplified linear chain with calibrated pressure input:

```
v_mic(t) = S * H_mic[p_L(t), p_R(t)]
x[n] = Q_bits( H_AA[ G * v_mic(t) ] / V_FS_peak ) at the sample instants
```

Here S is V/Pa, G is the voltage gain, V_FS_peak is the converter's peak full-scale
input voltage, H denotes the declared response/filter and Q is quantization.
Pressure, mic voltage, preamp voltage, PCM and playback gain must remain distinct.
Sensitivity is only one part of the frequency-dependent response.

Worked illustration, not calibration of the supplied WAVs: a 1 kHz tone at
0.02 Pa RMS is 60 dB SPL re 20 micropascals. At 20 mV/Pa it produces 0.4 mV RMS;
40 dB of preamp gain gives 40 mV RMS. With an ASSUMED full-scale sine input of
2 V RMS (2 sqrt(2) V peak), that is -33.98 dB relative to a full-scale sine.
A normalized PCM peak convention yields 0.020 peak and 0.01414 RMS. The RMS
number relative to 1.0 peak is -36.99 dB; do not silently mix the two dBFS
conventions. [DPA's dB definition](https://www.dpamicrophones.com/dict/db/)
provides the SPL reference. Bit depth/sample rate do not establish pressure
calibration, and 32-bit float storage cannot repair analog capsule/preamp overload.

## What 'more ear pressure' can mean

1. **Larger contact force:** changes indentation, contact area, friction and
   deformation; its conversion into pressure at the capsules is an unknown
   mechanics/acoustics relationship for this target.
2. **More occlusion or a tighter external seal:** changes the local air volume,
   leakage impedance, pressure relaxation and acoustic transfer. Low-frequency
   transients or changes in filtering are hypotheses to test, not prescribed pops.
3. **Greater acoustic pressure at the capsule:** within a linear calibrated
   response this raises voltage, until nonlinearities or overload matter.
4. **A stronger perceived close/pressing sensation:** a listening outcome, not
   another unit of force. Raising headphone gain is not a physical solution.

A bounded low-frequency cavity hypothesis can start from
`C_a dp/dt = Q_in - p/R_leak`, `C_a = V/(rho*c^2)`, with prescribed inward boundary
volume velocity Q_in. The resulting relaxation time is R_leak*C_a. The
[COMSOL lumped-circuit documentation](https://doc.comsol.com/6.3/doc/com.comsol.help.aco/aco_ug_pressure.05.068.html)
supports the compliance/circuit relation, not the unmeasured volume or leak of a
KU100 under contact. Higher-frequency resonances, nonlinear airflow, contact
feedback and changing geometry require additional treatment. F/A at the contact
patch is NOT the airborne p at a microphone; substituting one for the other
would be a unit-compatible but physically invalid shortcut.

## Implemented capture diagnostic, not a new pressure sound preset

`ku100sim/pressure_capture.py` accepts a known/simulated capsule-pressure trajectory
in Pa. It models a declared equalization high-pass, optional generic low-cut,
nominal sensitivity, preamp gain, numerical anti-aliasing and ideal 16/24-bit
quantization. It refuses overload rather than silently limiting or normalizing.
The generic equalization cutoff of 5 Hz and ADC full-scale voltage are explicit
ASSUMPTIONS, not manufacturer KU100 measurements. Frequency response, noise,
thermal effects and analog nonlinearities are not calibrated.

Its eight tests cover a 1 kHz worked example, zero input, constant-pressure decay,
stereo symmetry, low-cut behavior, anti-aliasing, overload refusal and invalid
inputs. The initial short anti-alias filter failed the 30 kHz test; an explicit
20 kHz passband / 24 kHz stopband Kaiser design replaced it, without changing the
test tolerance. These are component tests on artificial inputs, not a recording
comparison or a sound-quality verdict.

**The pleasant texture generator outputs uncalibrated digital audio. It is not
sent through this Pa-input diagnostic or relabeled as Pa.** No new force or seal
control is claimed in the published longer takes.

## Next pressure-specific experiment

Hold the object, gesture and microphone/recorder settings fixed. Record dry/wet
contact, stationary hold, slow/fast release, and open/partly sealed contact with
raw synchronized stereo, applied force, displacement/contact area and known
processing. Include a contact-free near-mouth control so internal mouth sounds
are not mistaken for force-driven ear sounds. Calibrate the capture chain using
a device-appropriate coupler and known sound pressure; distinguish the microphone
response from force-to-pressure transfer. No calibration source is played near
any person's ear as part of this software task.

Fit the minimum mechanics/transfer parameters that the measurements actually
constrain, then test new load and seal conditions. A conditional acoustic model
can be explored separately, but must be labeled learned/inferred, not pure
first-principles pressure simulation. The user's source recordings are useful
for timbre, but currently do not contain those synchronized physical labels.

## Reproduce the new examples

```bash
python -m pip install -r requirements.txt -r requirements-texture.txt
python -m unittest tests.test_pressure_capture tests.test_long_examples -v
python scripts/build_long_examples.py --out web/long/generated
# After the existing site/example prerequisites have run:
python scripts/package_long_site.py
node scripts/browser_long.mjs
```

The original texture model, native C++ mechanics, and existing fitting parameters
are unchanged. Existing output paths are refused by the generator. The separate
long-page packager retains the original site allowlist and 80 MiB size limit; it
does not copy a source tree or private reference folder into Pages.
