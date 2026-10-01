# Connected fingertip / silicone contact scene

Implemented for the user's next-stage request after the preferred near-ear fork
experiment. This is a first finite-geometry stage, not completion of the hand,
fluid, calibrated microphone-pressure or ASMR acceptance requirements.

## Delivered scene and shared architecture

`SimulationEngine(scene)` now accepts `coupled-solids/1` as well as the existing
`shared-mechanics/1` schema. It composes a reusable tetrahedral solid/contact
backend; no material name or audition ID selects a sound implementation. The
existing scalar graph and narrow-band compact-source operator remain available.

The new solid is a **34 × 8 × 24 mm box**, represented by **140 vertices, 432
positive-volume tetrahedra and 216 surface triangles**. Its short x-minimum edge
is clamped. Two translating spherical fingertip proxies (9 and 10 mm radii) have
mass, a compliant normal skin layer, tangential elastic/plastic friction memory,
and compliant position actuators. Contact loads act equally and oppositely on
solid and fingertip, so the fingertip does not simply follow an imposed path
through the body. Actuator targets pinch, hold, rub, reverse, squeeze and release.

These are NOT full anatomical fingers or an articulated hand. Joint dynamics,
fingerprint geometry, skin layers resolved as a continuum, self-contact of the
pad, fluid, adhesive peeling and bone conduction are not implemented. The
contact surfaces are geometrically smooth, with no old sinusoidal ridge pattern,
no imported source waveform and no audio-triggering event timer.

The main progress is genuinely connected deformation and two-way contact, not
merely making the old pad larger or adding sound filters. An unsupported water
or wetness field fails validation; it does not append a squish soundtrack.

## Source material measurements actually inspected

The published [Roels et al. elastomer dataset](https://zenodo.org/records/14983287)
was downloaded through the hash-checked `inspect-elastomer-data` workflow.
The uniaxial compression archive MD5 is
`1d445b2cc7a2393e62b8017f69710ca0`; its SHA-256 is
`7acde7e17883150264a528a55bced8d1828c8f70179066df81ad4f6545c5b856`.
Five Ecoflex 00-30 CSV members were inspected (201 rows each). They report nominal
strain in percent and nominal stress in MPa. These are mechanical data, not ASMR
recordings. Raw CSVs and the downloaded archive are not published in the site.

The fitting script uses only files 1–3 over **5–20% reported compression** and
fits the ideal homogeneous incompressible neo-Hookean relation
`compressive nominal stress = mu * (lambda^-2 - lambda)`. No offset or scale
beyond mu is fitted. The resulting effective `mu = 52596.06184931944 Pa` gives
relative stress norms 2.66%, 4.61%, 4.38% on fitting files, and 4.86%, 6.75% on
files 4–5, which were reserved from fitting but inspected in this development.
Those numbers do NOT validate the dynamic contact sound.

See `models/materials/ecoflex-compression.json` for all individual file hashes,
fit scope and results, and `scripts/fit_silicone_compression.py` to reproduce.

The [authors' paper](https://doi.org/10.1002/aisy.202500699) warns about fixture and
crosshead-displacement effects and uses a more elaborate combined-data inverse
finite-element fit. We have NOT reproduced that procedure or its complete Ogden
model. Our compression approximation is not identified intrinsic multiaxial
material behavior. The nominal density of 1070 kg/m3 comes from the
[manufacturer](https://www.smooth-on.com/products/ecoflex-00-30/).
The 12 s and 177 s relaxation times and small memory magnitudes are rounded priors
informed by the paper's Table 3, not newly fitted audio-band loss. Bulk modulus,
viscosity, fingertip layer and all friction parameters are explicitly unmeasured.

## Finite-strain model

For deformation gradient F, J=det(F), and I1=F:F:

```
Psi_dev = mu/2 * (J^(-2/3) I1 - 3)
Psi_vol = K/2 * (J - 1)^2
```

The nominal stress is the derivative of elastic energy. Positive objective
viscosity uses the symmetric spatial velocity gradient D:
`P_visc = J [2 eta dev(D) + eta_bulk tr(D) I] F^-T`.
Its work rate is nonnegative. Two reference Green-strain deviatoric memory arms
use `A_dot = (dev(E)-A)/tau` with energy `mu_arm ||dev(E)-A||^2` and the matching
stress and dissipation. This is a declared finite-strain extension, not a claim
of a fully identified silicone constitutive law.

Standard linear tets can suffer volumetric locking. The initial element-volume
variant and its unfavorable acoustic refinement are retained under
`validation/hand/initial/`. The selected model uses energy-derived **average
nodal volume** for the bulk term: nodal reference volume is the sum of incident
tet volumes/4, nodal J is volume-weighted, and each tet receives the average of
its four nodal pressures. The derivative is checked independently. This follows
the single-material average-nodal-pressure principle discussed in
[Non-locking Tetrahedral Finite Element for Surgical Simulation](https://pmc.ncbi.nlm.nih.gov/articles/PMC4477870/).
It is not an unconditional locking-free or spatial-convergence certificate;
[assessments of nodal averaging](https://doi.org/10.1002/cnm.697) also report
pressure-field limitations. A mean nodal mechanical pressure is NOT microphone
pressure. The ordinary element-volume law remains an explicit model option.

The explicit native update uses velocity-Verlet-style drift/kick, exact
exponential memory relaxation for the current strain sample, and constitutive
contact updates. Actual work, stored energy and dissipation are reported. It is
NOT the old graph's exact discrete-gradient energy integrator. Numerical energy
residuals are retained; they are not zeroed by renormalizing state.

## Contact and force meaning

Three barycentric quadrature points per boundary triangle couple the solid to
each sphere. The reference patch area scales normal and tangential stiffness.
Normal compression gives a repulsive layer force; normal viscosity dissipates
energy on approach. A tangential bristle stores relative displacement, is
projected onto the tangent plane, and yields at the load-dependent friction cap.
The velocity-weakening variant interpolates between an assumed static and dynamic
coefficient; a rate-neutral variant holds those equal. Loss includes slip,
projection and separation resets. No spontaneous audio continues after detachment.

The normal layer is a compliant-surrogate approximation, not an interpenetration-
free collision solver. Significant layer compression is reported rather than
being misrepresented as full finite-strain fingertip tissue. The stronger cases compress the assumed linear skin layer by about 75%;
that regime is not qualified as physiological skin. The light-contact case is
about 27%. These are explicit model limitations, not measured skin strains.
The scene is one
solid plus sphere actors, not arbitrary all-body collision. C-IPC is relevant to
future general contact but is NOT installed or claimed as the present algorithm:
https://ipc-sim.github.io/C-IPC/ .

Force readings are newtons of computed actor reaction. There is no conversion of
`force/contact area` into assumed air pressure at the user's ear and no pressure-
feeling slider. The user has not accepted the ASMR sensation of this scene.

## Binaural sound, not noise or replay

The source operator sums the actual deforming surface's normal volume velocity
on six faces, differentiates it, and uses six compact-source contributions through
the existing measured KU100 receiver. The source coordinates are projected onto
the measured horizontal 0.25 m circle; this is a deliberate bounded approximation,
not closer-than-measured data. Surface contributions are summed coherently.

This is a radiation proxy, not a BEM solve or a calibrated Pa recording. Near-field
shape/scattering, fingertip acoustic obstruction and ear-contact transmission are
missing. A 30 Hz high-pass, numerical band limiting and a common fixed listening
gain of 600 are disclosed. All four contact files have two active, nonidentical
ears. There is no independent normalization of light/firm scenes or ear channels,
no added bass oscillator, stochastic texture layer, wet sound, or source clip.

The two fork-field algorithms and settings the user preferred are preserved as
an additive `/fork-radiation/` page. They still use the previously documented
ideal-sphere prediction below measured KU100 ranges; this does not calibrate the
new silicone source. See [FORK_NEAR_FIELD.md](FORK_NEAR_FIELD.md).

## What the numerical results establish

Independent tests check elastic energy/stress gradients, rigid-rotation
objectivity, viscous work, uniaxial stress, nodal-volume energy derivatives,
positive mesh volumes, closed surface orientation, contact feedback, clamped
support, block-size invariance, metadata independence, zero contact, no file
reads during native stepping, and invalid controls. The native state and audio
operators are separately testable.

The fixed 1.5 s refinement experiment is distinct from the full five-second
listening runs. With nodal averaging, 96-to-192 kHz refinement gives approximately
0.00064%/0.00060% reaction-force norm differences and 0.433% surface-flux difference.
The default-to-finer mesh comparison still gives **5.17%/5.03% force differences**
and **41.56% surface-source difference**. The declared 5% mesh criteria therefore
FAIL; they were not relaxed. The initial ordinary-tet source difference was
53.97%. This is progress in source sensitivity, not a converged acoustic result.

These force and sound measures should not be conflated. Tone concentration can
still arise from unresolved geometry/contact and unmeasured constitutive choices.
The new velocity-weakening rubbing source has significant tonal content; it has
NOT passed a reference-based skin/silicone timbre test. More geometric complexity
alone does not establish realistic ASMR. The UI calls this a research comparison.

## Next requirement, kept separate

A thin-walled pouch with water and air requires an actual hollow shell, free
surface, fluid/solid feedback and separately qualified fluid acoustics. It is not
implemented by the solid-pad scene, and no flowing-water visualization or sound
is fabricated. Existing two-way fluid/solid solvers are candidates for integration
behind the shared scene API: https://splishsplash.readthedocs.io/en/latest/about.html .
Fluid pressure from an incompressibility constraint is not automatically audible
pressure; the distinction remains in the original next-scene requirements.

Before attaching that extra subsystem, the concrete gates are a better identified
skin/silicone contact law, refined force/source fields, measured source radiation,
and a matched reference comparison. Preserve the user's preferred fork evidence;
do not replace it with a claim that mechanical success implies ASMR acceptance.

## Reproduce

```
python scripts/fit_silicone_compression.py --help
python -m unittest tests.test_solid_scene tests.test_compact_radiation -v
python scripts/build_hand_scene.py
python scripts/validate_hand_scene.py --out web/hand/generated/refinement.json
python scripts/build_fork_radiation.py --out web/fork-radiation/generated
# After the existing example-generation prerequisites:
python scripts/package_hand_site.py
node scripts/browser_contact.mjs
```

The default generator refuses existing output directories. No raw data download is
needed to render from the compact material parameters. Code/data/model/recording
provenance are recorded independently. GitHub CI and live-site results belong to
specific executed commits; this document is not itself proof of deployment.
