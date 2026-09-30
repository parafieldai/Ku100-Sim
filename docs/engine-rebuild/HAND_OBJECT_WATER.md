# From an isolated texture to coupled hand/object/liquid interactions

30 September 2026. Baseline main: `56275aa5fc39a0ae1defa26fb4c263f64147926d`.

## Actual cause of the rejected silicone sweep

The published `scenes/unified/silicone-sweep.json` is not a named silicone rubbing
against a named counterface. It contains three unmeasured normal mass/spring
contacts, each driven by three sinusoidal height components. No human finger,
second material, finite-strain mesh, friction, adhesion or water model determines
that texture. Material labels do not establish those missing mechanisms.

The fastest prescribed travel is 18 mm in 0.95 s with quintic interpolation.
Its peak speed is 1.875 * 0.018/0.95 = 0.0355263 m/s. In patch 0, spatial periods
of 400, 160 and 65 micrometres produce instantaneous driving frequencies up to
88.82, 222.04 and 546.56 Hz. They accelerate/decelerate with the imposed travel,
so chirp-like components are built into the source. The baseline WAV's strongest
Welch-PSD peak is 539.06 Hz. This supports a source-model diagnosis, not a claim
that true silicone cannot squeak. The other free-coordinate frequencies and
loaded contact frequencies are also unmeasured.

Softness alone does not dictate a low-pitched recording: contact stiffness,
surface chemistry and the slip process can matter. PDMS experiments [1] show that
stiffness, oligomers and pendant chains affect different portions of stick/slip.
Those results do not calibrate this proxy or identify human skin as its counterface.
The old source is relabeled as a rejected periodic-ridge diagnostic on this branch;
no EQ or pitch change is presented as the fix.

## Implemented first shared-engine extension

This change adds **explicit dynamic bodies and pairwise interactions to the
existing `SimulationEngine` and native kernel**, not separate Hand/Water/Silicone
simulators. Nodes remain one-dimensional reduced normal coordinates. Multiple
bodies own those coordinates; contacts require two different named bodies with
material descriptions. These descriptions are metadata, not a covert preset switch.

Two reusable laws are implemented:

- `normal_contact`: one-sided elastic penalty between two dynamic endpoints.
- `viscoelastic_link`: relative-coordinate linear/quartic elasticity, viscous
  damping and one Maxwell relaxation arm between two endpoints.

For relative coordinate `z = s*(q_a - q_b) - gap`, a contact stores
`V = k*max(z,0)^2/2`. Its endpoint forces are equal and opposite, and it cannot
pull when detached. Both endpoints participate in the existing implicit solve;
a fingertip is not merely an externally imposed waveform after the render.

The viscoelastic link uses `V = k2*z^2/2 + k4*z^4/4 + kr*r^2/2`,
`r_dot = z_dot - r/tau`, plus nonnegative viscous damping. Its same-state discrete
gradient supplies both endpoint reactions. Energy accounting includes internal
storage and dissipation; external work remains at the actual actuators. The
potential-based approach is informed by [2], not a reproduction of every system
in that paper.

The native layout appends one memory coordinate per interaction before the
energy/work/loss/balance columns. `interaction_readout()` returns endpoint force,
strain and contact state; these endpoint forces are not confused with the
step-average discrete-gradient force. The CLI exports matching column headers
and applies parameter scaling to interactions as well as original node terms.

`scenes/interactions/opposed-grip.json` contains a thumb-like compliant tip,
two reduced coupon coordinates, and an opposing index-like tip. Two unilateral
contacts compress the coupon's internal viscoelastic link, then release it. All
parameters are dimensioned but illustrative. There is no periodic roughness or
fake squish layer. It is **a normal-grip mechanics test, not a 3-D hand, named
silicone formulation, or a newly accepted ASMR effect**.

Any acoustic export still passes through the existing measured KU100 receiver;
there is no duplicated-mono delivery. The weighted-velocity source proxy remains
uncalibrated. This work does not solve sound radiation merely by adding contacts.

## What the genuinely more complex scene needs next

A hand has articulated motion and multiple changing contacts. The object has a
spatial geometry and constitutive law. Supporting gestures such as squeezing,
rolling between fingers, sliding and release requires those interactions to
change the shared scene state. The hand's movement must cause contact forces;
reaction forces must affect object motion/deformation. A complete finite-strain
mesh and frictional contact are separate from the current reduced normal stage.

A useful scene contract therefore separates:

1. Hand skeleton/trajectory, compliant fingerpads and contact geometry.
2. Rigid or deformable objects, supports, joints and self-contact.
3. Named contact pairs, surface state, friction and applicable adhesion.
4. Fluids and their interfaces, where present.
5. Acoustic source locations, radiation and the two microphone receivers.

A water-filled silicone pouch should involve pouch deformation displacing water,
water reaction loading the pouch, trapped air where present, and eventual surface
or outlet events. A bottle has a different shell/opening/grip state. A saturated
sponge requires porous transport as well as deformation. These are shared laws
composed into objects, not independent audio sample players.

## Water must be actual state, not a damped ring or added noise

Two-way fluid/solid methods [3] show how pressure constraints and solid integration
can be solved together. SPlisHSPlasH [4] provides an existing C++ research candidate
with rigid-fluid and deformable-solid coupling, surface tension and viscosity.
It is a candidate offline physics adapter to evaluate, not a library installed or
validated by this patch. Its visual fluid outputs are not automatically audio.

In particular, an incompressibility solver's pressure field is not a ready-made
48 kHz microphone signal. Harmonic Fluids [5] acoustically augments fluid motion
with bubble creation, vibration, transport and radiation rather than treating a
slow fluid simulation as a complete compressible-acoustic solution. Other fluid
and structural source mechanisms can contribute; do not assume every squish is
a bubble. A sponge requires Darcy-type pore transport or another supported
porous law; [6] treats fluid/porous-material coupling, not a finished ASMR renderer.

The shared engine should coordinate appropriate time scales: hand motion,
contact/deformation and fluid integration, then audio-rate structural/acoustic
response. It should not run millions of fluid particles at an arbitrary 48 kHz
rate or upsample slow pressure artifacts and call them recorded sound.

## Real data and acceptance

Use a specified pair such as a skin/fingerpad surrogate and a named silicone
coupon, then add water as a separate condition. Roels et al. [7] provide named
silicone compression/relaxation measurements and data [8]. Their slow mechanical
measurements do not establish audio-band damping, skin friction, or ASMR timbre.
A material-specific calibration needs actual geometry plus observations relevant
to that interaction. Anonymous “silicone” is not enough.

Acceptance requires matched motion/contact information and stereo recordings,
plus listener comparison to the desired effect. Keep force/volume conservation,
solver convergence, acoustic prediction, and subjective sound quality separate.
Passing two-body collision tests is not a positive listening verdict.

## Reproduce and inspect the stage

```bash
python scripts/prepare_ku100.py --download
python -m unittest tests.test_interactions tests.test_unified tests.test_binaural tests.test_unified_publication -v
python scripts/check_interaction_stage.py --out validation/local/grip-check
```

The new tests compare collisions and relaxing links with independent continuous
ODE solutions, momentum conservation, contact/release and nonnegative loss. They
cover block invariance, metadata independence, live forces, paired-material
validation, rejected fake water/wetness controls, no source reads and the complete
binaural/CSV export. The old source/receiver tests remain in the selected suite.

No source recording was fitted for this change. No new water simulation, hand
mesh, tangential contact law, realistic squish clip, or listening success is
claimed. The development branch does not replace the deployed audio with another
unsupported result. The earlier fork-radiation patch is separate local work and
has not been silently merged by this change.

## Primary sources

[1] Xue et al. (2016), Stick-Slip Friction of PDMS Surfaces for Bioinspired Adhesives:
https://pubs.acs.org/doi/10.1021/acs.langmuir.6b00513

[2] Bilbao, Torin and Chatziioannou (2014), Numerical Modeling of Collisions in Musical Instruments:
https://arxiv.org/abs/1405.2589

[3] Chentanez et al. (2006), Simultaneous Coupling of Fluids and Deformable Bodies:
https://graphics.berkeley.edu/papers/Chentanez-SCP-2006-08/index.html

[4] SPlisHSPlasH, official implementation and features:
https://github.com/InteractiveComputerGraphics/SPlisHSPlasH
https://splishsplash.physics-simulation.org/features/

[5] Zheng and James (2009), Harmonic Fluids:
https://research.cs.cornell.edu/HarmonicFluids/

[6] Ren, Xu and Li (2021), Unified particle system for multiple-fluid flow and porous material:
https://cronfa.swansea.ac.uk/Record/cronfa57521
https://github.com/BenXu86/PorousSimulation

[7] Roels et al., A Standardized Framework for Elastomer Characterization in Soft Robotics:
https://advanced.onlinelibrary.wiley.com/doi/10.1002/aisy.202500699

[8] Accompanying material data:
https://zenodo.org/records/14983287

These sources were read for methods and scope; external solvers and new material
recordings were not downloaded/executed in this stage.
