# Fork pressure / vibration complaint: missing source radiation

Date: 2026-09-30. Local research revision of the application at `51f8390`; main
was read at `56275aa5fc39a0ae1defa26fb4c263f64147926d`. This is not a new deployed
or perceptually accepted result. No matched physical tuning-fork recording was
available or used in this experiment.

## Diagnosis of the previous demo

The fundamental's mass was 0.002 kg and viscous damping was 0.006 N s/m, giving
amplitude decay alpha = c/(2m) = 1.5 /s. A free ring loses 39.0865 dB over three
seconds; its half-amplitude time is 0.4621 s. Head/receiver motion is an additional
change. The prior scene changed source azimuth on a 0.25 m head-center circle,
but did not rotate the fork about its own stem or represent its opposing tines'
radiation. Its mechanical readout was weighted velocity, not a measured volume
source or calibrated pressure.

The user reports absence of the desired pressure/vibration character. That
listening failure remains the acceptance status; stereo-channel and software
tests did not overrule it.

## Reusable implementation, not a ForkSimulator

The common `SimulationEngine` gains a `render_radiated(configuration)` method.
It delegates to a new `CompactRadiation` component. A configuration specifies
signed source elements, pose trajectories, receiver approximation, and a mapping
from mechanical node IDs to emitting elements. Object names do not affect the
algorithm. Existing measured-only `render_binaural()` and all source parameters
are unchanged. Unsupported driven/nonlinear/contact graphs are rejected on this
new narrowband path; the general mechanical engine is NOT restricted by it.

The scenes use free-ring linear state from the actual native kernel, not a
source performance clip. A free oscillator's complex coordinate can be recovered
from its real state as

```
z_q = q - i (v + alpha*q)/omega_d
s = -alpha + i*omega_d
z_acceleration = s^2*z_q
```

This is a quadrature representation of the existing state, not a new sinusoidal
sound clip. Source-to-volume coupling remains relative and unmeasured. It does
NOT identify radiating area, true modal shapes, or absolute source strength.

For the main proposed fork pattern, four elements lie at x = -16,-6,6,16 mm,
with weights +1,-1,-1,+1. This is a compact approximation of two opposing dipoles,
not a scanned fork geometry. Other element arrays use the same operator.

## Field equation and receiver anchoring

Using the exp(+i omega t) convention, the free field is a sum of

```
w_j * exp(-i*k*distance_j) / distance_j
```

The signed terms cancel differently as the source rotates and approaches. No
sinusoidal gain LFO, arbitrary heartbeat, bass oscillator or per-ear normalization
is added. The loudness variation emerges from the array geometry and wave phase.

The sphere-surface Green function is evaluated by the outgoing spherical-Hankel
series, then conjugated for the chosen time convention:

```
G_e(f,s) = conjugate[-1/(k*a^2) * sum_n (2n+1)
                       * h_n(k*|s|)/h'_n(k*a)
                       * P_n(dot(s/|s|, ear_direction))]
```

The numerical implementation uses ratios of successive Hankel functions. This
avoids overflow at large expansion orders and low frequencies close to the sphere.
Receiver surface directions are +y left and -y right. The assumed sphere radius
is 0.0875 m; it is not a newly measured KU100 head or pinna.

The measured 0.25 m KU100 response H_e is divided by the ideal-sphere response to
one central monopole at the same angular anchor. The predicted finite-array
field at the requested pose then multiplies that ratio:

```
T_e = H_e(anchor) * sum_j w_j G_e(source_j) / G_e(anchor_monopole)
```

This avoids stacking two complete head filters. At the anchor with one unit
central source, it recovers H exactly by construction. That identity is a
contract test, NOT independent real-world validation of extrapolation.

The range-frozen residual correction is a hypothesis, especially near the ear.
No new near-contact measurement or pinna model is claimed. The old measured-only
receiver still rejects distances below 0.25 m; its guard is not weakened.
This separate prediction path can place the source center 3 cm outside the
assumed sphere. With these offsets, the closest element can be 1.4 cm outside
that sphere. Neither number is a measured distance from an artificial pinna.

The operator is evaluated at each modal frequency with slowly varying pose.
Complex coefficients are interpolated at a declared pose rate. The free carrier
is transported without linear audio interpolation; a common envelope flight
delay is retained. This is narrowband/quasi-static, not a full broadband retarded
moving-boundary, strike or contact calculation. Radiation feedback to the fork,
stem contact, liquids, air seals, and bone/skin coupling are not implemented.

## Auditions

Seven new ten-second stereo files:

1. 256 Hz approach, rotate and withdraw, preserving time-varying range gain.
2. 512 Hz long ring, single central source, at measured anchor radius.
3. 512 Hz rotating compact array, at anchor center radius.
4. 512 Hz rotating array near the model head.
5. 256 Hz rotating array near the model head.
6. 128 Hz rotating array near the model head.
7. 256 Hz close prediction with source at the left side.

All use the same source engine and radiation component. The ring damping is
0.2 /s, an illustrative longer-ring setting, not a fitted material constant.
The 128 Hz case is not described as an identified weighted fork. The receiver
bank below roughly 200 Hz includes analytic extension and is not independent
low-frequency pressure validation.

Each stereo audition gets one shared scalar to RMS 0.04, capped at peak 0.35.
No ears are matched separately and no dynamic limiter is used. This lets listeners
compare character without a large loudness jump. Relative changes *within* each
file are retained, but absolute distance levels between separately matched files
are not a calibration result. Headphone level starts at -12 dB. Increasing volume
to force a tactile effect is not an acceptance procedure.

Source state begins already ringing. Declared 20 ms onset and 200 ms end fades
are for playback boundaries; they do not stand in for simulated mallet attacks
or a damping hand. Audio is Float32 stereo, 48 kHz. All seven channels pairs are
active and nonidentical. No mono preview is published.

## Executed tests

57 selected native/API/receiver tests passed, including 19 new radiation tests.
This is not a new full 191-test application CI run.

New tests cover independent spherical-Bessel evaluation, Neumann boundary
condition, static/free-field limits, expansion refinement, finite-source
superposition, analytic quadrupole limit, near/far directivity, measured-anchor
recovery, a static free ring against the existing native measured-FIR renderer,
name invariance, unsupported-model rejection, silence, recording-read refusal,
and pose refinement.

Full ten-second 128/256/512 Hz close-ring comparisons pass the predeclared bounds:
per-ear 240-to-480 Hz pose error <0.1%, mechanical 192-to-384 kHz relative error
<1e-6, expansion extra-48-term relative error <1e-9. Actual worst values are about
0.000593%, 2.57e-11 and 5.80e-16 respectively. Numerical agreement does not validate
the assumed geometry, frozen receiver correction or listener response.

The free-space directivity test has four maxima per turn at 5 cm and two at
2 m for a 426 Hz finite array. This reproduces the *qualitative theoretical
near/far behavior*, not a digitized fit to the paper's microphone measurements.

Local Chromium 144 ordinary file navigation was blocked by administrator policy;
that failure is retained. A separate explicitly in-memory component test passed
actual playback, completed seeking, exact stereo decoding, download hashes,
exclusive playback, and desktop/mobile layout for all seven files. It issued
no HTTP requests. It is not a normal-navigation or Pages deployment pass.

Current GitHub discovery exposes no create/update/push actions, and the runtime
could not resolve GitHub for Git transport. Therefore this experiment and its
Git patch are delivered locally; the live site remains unchanged. No force push,
new remote workflow, or altered site deployment is claimed.

## Primary research and measurement notices

- Russell (2000), *On the sound field radiated by a tuning fork*, DOI
  10.1119/1.1286661. Author's accompanying explanation describes four signed
  point sources and near/far cancellation:
  https://www.acs.psu.edu/drussell/Demos/forkanim/forkanim.html
- Russell's modal demonstrations distinguish the fundamental, clang and other
  mode patterns. This implementation uses illustrative parameters, not those
  meshes or copied audio: https://www.acs.psu.edu/drussell/Demos/TuningFork/fork-modes.html
- Duda & Martens (1998), range-dependent spherical head transfer, DOI
  10.1121/1.423886: https://escholarship.org/uc/item/0kb7r9m9
- Russell, Junell & Ludwigsen (2013), reactive near-field intensity versus
  radiated energy: https://pure.psu.edu/en/publications/vector-acoustic-intensity-around-a-tuning-fork/
- DPA pressure-microphone transduction and static pressure equalization:
  https://www.dpamicrophones.com/dict/pressure-microphone/
- KU100 receiver bank: https://zenodo.org/records/4297951 ; source bank SHA-256
  `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712`.
  Johannes M. Arend, Annika Neidhardt, Christoph Poerschmann. Source embedded
  notice CC BY-SA 3.0; repository records metadata CC BY 4.0 separately.
  Existing data notices remain, without inferring a new license.

A pressure microphone encodes changing air pressure. The ear/skin mechanical
force of touching a fork is not a second channel hidden in the WAV. The aim of
these tests is the audible close vibrating character, not a claim of delivered
skin force or bone conduction. No human listening verdict is filled in.

## Reproduce

```
python scripts/prepare_ku100.py --download
python -m unittest tests.test_unified tests.test_binaural tests.test_compact_radiation -v
python scripts/validate_fork_radiation.py --out validation/local/fork-numerical.json
python scripts/build_fork_radiation.py --out outputs/fork-radiation --html outputs/fork-radiation.html
python scripts/browser_fork_radiation.py outputs/fork-radiation.html --out validation/local/fork-browser
```

Use a new output directory. Browser test uses a system Chromium path on Linux;
`--in-memory` explicitly selects the narrower component test and reports it as
such. The normal application build and live Pages workflow have not been extended
to publish this separate experiment yet. A later release should run its full CI
and integrate a bounded publication path without regenerating the older accepted
texture waveforms merely because documentation or this source module changes.
