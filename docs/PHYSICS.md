# Native contact mechanics and acoustic fixture

The native C++17 solver is a generic bilateral laboratory fixture: two elastic plates, two small air chambers, a connecting air duct, and an outward vent on each chamber. A prescribed tool contacts one plate. The geometry and material constants are declared parameters, not measured Neumann KU100 internals. The two contact outputs are the solved chamber pressures in pascals. A measured KU100 airborne response is a separate receiver operation; it is not applied between a contacting finger and either chamber.

This model makes a physically accounted bilateral transmission experiment possible. It does not establish that a real dummy head contains this duct, that a chamber pressure equals its capsule pressure, or that wet contact sounds realistic. External head diffraction, a shared head shell, pinna geometry, compliant fingertip shape, capillary bridges and calibrated transducers are not in this fixture.

## States and units

For each plate, mass-normalized modal displacement and velocity are `q` and `v`. The remaining states are chamber/duct-cell pressures `p` [Pa], duct and vent volume flows `Q` [m³/s], and a radiation state `z` [m³/s]. The contact indentation `delta` [m] is determined by tool displacement minus the plate's projected normal displacement. Tool position and speed are external energy-supplying controls.

All arithmetic in the physical core uses double precision. The core has no microphone gain, HRIR lookup, normalization, limiter, waveform asset, audio noise generator, or per-ear output adjustment.

## Plate and finite contact patch

Each plate uses the simply supported rectangular Mindlin ansatz, for positive integers m,n:

```
w = W sin(alpha x) sin(beta y)
theta_x = X cos(alpha x) sin(beta y)
theta_y = Y sin(alpha x) cos(beta y)
alpha = m pi / width; beta = n pi / height
```

With area factor A/4, the mass matrix is diagonal with entries `rho h`, `rho h³/12`, `rho h³/12`. Let `D = E h³/[12(1-nu²)]` and `S = (5/6) E h/[2(1+nu)]`. The stiffness matrix before multiplication by A/4 is

```
[ S(alpha²+beta²)     -S alpha                     -S beta                  ]
[ -S alpha           D(alpha²+(1-nu)beta²/2)+S     D(1+nu)alpha beta/2      ]
[ -S beta            D(1+nu)alpha beta/2           D(beta²+(1-nu)alpha²/2)+S]
```

The implementation solves the symmetric mass-normalized 3×3 eigenproblem for each pair. Thus `Phiᵀ M Phi = I`, and every retained coordinate has energy `(v_i² + omega_i² q_i²)/2`. A damping force `-2 zeta omega_i v_i` removes energy.

The fixed candidate set is `1 <= m,n <= 96`, with all three branches, sorted by eigenfrequency. Retaining more modes adds a nested prefix. The default retains 128 modes per plate; the permitted maximum is 1,024 and plate aspect ratio is restricted to 0.25–4. A count is a truncation control, not an audible quality guarantee.

The traction footprint is a normalized Gaussian centred at `(0.43 width, 0.47 height)` with standard deviation `contact_radius/2`. Its analytic projection supplies a factor `exp[-sigma²(alpha²+beta²)/2]`. The footprint must stay small relative to the plate; the validated size limit makes the neglected Gaussian tails at plate edges very small. A moving material texture passes this stationary footprint; this is not a finger trajectory moving between different positions on a head.

Let `b_i` be the normal-force projection, `t_i` the projection of the tangential surface displacement `-(h/2) theta_x`, and `a_i` the integral of mode i's normal displacement over the plate. The same coefficients are used in both directions:

```
contact normal velocity = bᵀ v       modal normal force = b F_n
contact tangential velocity = tᵀ v   modal tangential force = t F_t
chamber volume velocity = aᵀ v      modal pressure force = -a p
```

These adjoint maps preserve interface work. There is no independent force, radiation or pressure gain depending on retained mode count. The prescribed preload uses the static normal compliance of the same complete candidate space for every truncation, so a mode-refinement test does not silently change its excitation. The runtime dynamics themselves have no residual-flexibility correction: contact compliance and output pressure must still be checked for convergence.

## Contact, friction and the limited fluid branch

The normal spring has nonnegative stored energy

```
V(delta) = k max(delta,0)^(5/2) / (5/2).
```

The spring force at a step is the discrete gradient `(V(delta1)-V(delta0))/(delta1-delta0)`. An algebraically equivalent divided difference avoids cancellation when positive indentations are nearly equal. This makes spring work equal its energy change even across contact and release.

Closing-only normal damping acts at the solved relative midpoint velocity when either step endpoint is in contact. Tangential dry friction uses `F_t = mu F_n tanh(v_relative/v_scale)`. Its force times relative slip speed is nonnegative. This smooth dissipative law does not model a static bristle store, true sticking, velocity-weakening friction, or adhesive bond rupture. Those mechanisms require additional physical state and force measurements.

The fixed wetness parameter scales only an idealized Newtonian film's viscous contribution. For a circular parallel patch, its normal coefficient is `3 pi eta radius^4/(2 film_thickness^3)`; the shear coefficient is `eta pi radius²/film_thickness`. Normal film damping is closing-only, so the model does not invent unlimited tensile suction on separation. The gap is a declared effective film thickness, not a simulated free surface. Dry friction is not altered by an unmeasured wetness multiplier.

This branch has nonnegative dissipation, but it is not a complete wet-contact model. It omits liquid-volume transport, cavitation, drying, capillary attraction, changing real contact area, hydration and bubbles. A real film thickness may vary rapidly and may invalidate the parallel-plate reduction. No liquid sound event is generated merely because wetness is positive.

The normal and tangential contact forces are solved together through the two-port structural/acoustic admittance. A safeguarded scalar normal solve encloses a monotone tangential solve. The code checks the force residual and throws if it cannot converge; it does not silently reuse an unconverged force.

## Distributed acoustic connection and vents

Each end chamber has compliance `C = volume/(rho_air c²)`. The connecting duct has a uniform cross section and a finite-volume sequence of pressure cells and volume-flow edges. For cell length dx and area A:

```
C_cell = A dx / (rho_air c²)
L_edge = rho_air length / A
R_edge = 8 eta_air length / (pi radius^4)
C_j dp_j/dt = Q_in - Q_out
L_e dQ_e/dt = p_left - p_right - R_e Q_e
```

The two edges joining the end chambers to the first/last duct cell use half-cell length. The default uses 32 cells over 0.18 m. Finite-volume dispersion must be checked by increasing the cell count; midpoint stability does not eliminate it. This is a one-dimensional plane-wave model with a simple quasi-steady wall resistance. It does not reproduce high-frequency viscothermal boundary layers or transverse duct modes. A lumped end chamber also eventually ceases to represent a spatially uniform pressure field.

Each vent has its declared air inertance and Poiseuille resistance, followed by an equivalent pulsating-sphere radiation impedance. With sphere radius equal to vent radius,

```
R_rad = rho_air c / (4 pi radius²)
tau = radius/c
tau dz/dt = Q - z
p_rad = R_rad (Q-z).
```

This branch stores `R_rad tau z²/2` and dissipates `R_rad (Q-z)²`. Its free-field pressure observation at radius r is `(radius/r) p_rad`, before flight time. The core exposes r=0.25 m observations separately for the two vents. A small vent is not literally a sphere: this is a declared passive equivalent radiation load, not a solved pinna/head scattering problem. The measured airborne receiver may consume one vent as a source at a measured external position. Neither vent observation is mixed into the contact ears by the physical core.

## Time integration and work balance

All linear structural, chamber, duct, vent and radiation equations use implicit midpoint at a common integration rate. Eliminating each mode gives diagonal mobility terms; eliminating flow edges gives a positive-definite tridiagonal acoustic system. It is factored once. A precomputed pressure response column supplies the low-rank contact feedback, so nonlinear iterations operate only on the two contact ports.

For a full step the code checks the original states, not an energy-clamped surrogate:

```
stored_energy + accumulated_dissipation - accumulated_tool_work
```

Stored energy includes every modal kinetic/elastic term, contact potential, all pressure compliances, duct/vent inertances and radiation storage. Dissipation includes structural damping, contact damping, slip/film work, duct/vent resistance and radiation. Tool work is `F_n Delta y + F_t v_tool dt`. No correction rescales state to hide a residual.

For fixed physical parameters the linear midpoint rule and discrete contact gradient make this work identity hold up to solve and floating-point error. This is a numerical accounting result; it does not establish accurate geometry, good bandwidth, a calibrated output level or realistic sound. Varying wetness/material stiffness during a render would require accounting for parameter work; the current API deliberately holds them fixed.

## Prescribed experiments and observations

`stroke` and `press` use a smooth engagement envelope and release by 75% of the requested duration. `stroke` additionally slides a deterministic spatial texture at the requested speed. The final 25% is unforced decay; it need not contain the entire physical decay. `tap` uses one short smooth indentation pulse, followed by decay. `silence`, or exactly zero load, leaves the relaxed fixture at rest.

`load_n` sets a nominal static preload through the declared contact spring and the reference static plate compliance. It is not a force servo and it does not cap transient forces. Texture is a fixed sum of spatial sinusoidal components with seed-controlled phases and metre-valued roughness. Its spectral shape is an explicit uncalibrated surface assumption. It drives the contact geometry; it is not added to the output as audio.

The default nominal load is **0.01 N**, a gentle contact. A preliminary 0.6 N
setting displaced this soft plate by over three thicknesses and produced high
pipe-flow Reynolds numbers; it was rejected as a default even though its discrete
energy check passed. The core now reports peak contact-point displacement and a
conservative global plate-displacement bound `sum_i |W_i q_i|`, plus vent/duct
Mach and Reynolds numbers. Because the spatial sine functions have magnitude
at most one, this bound covers every point on both plates. It marks
`regime_valid=false` with explicit reasons if the bound exceeds 0.1 thickness,
Mach exceeds 0.05 or Reynolds exceeds 1,000. These conservative engineering
screens are not universal material/flow transition thresholds, and passing them
does not validate spatial resolution, frequency-dependent wall losses or device
calibration. The displacement bound may conservatively flag a case whose actual
spatial maximum is smaller; the returned waveform is not altered to force a
passing flag.

Each output sample observes the end-of-step state at `(index+1)/integration_rate`. Trace rows contain exact pressures at their own times. Output decimation and optional receiver processing are outside `physics.cpp`; no gain should be applied before raw pressure and energy diagnostics have been saved.

## Required validation before a device-fidelity claim

Run `python scripts/validate_physics.py` from the repository to reproduce the
native contact, mirror, silence, wet, tap, mode-count, integration-rate and duct
refinement probes. The output is `validation/physics-convergence.json`, including
the compiler, source hashes, unnormalized pressure metrics, energy residuals and
band-power fractions. The probe is separate from microphone/receiver processing.
Its pass/fail assertions concern this fixed test set; its high-band metrics must
be read alongside the excitation fractions.

1. Refine structural count, duct cells and integration rate separately, holding physical input trajectories fixed. Compare forces, contact mobility and both pressure spectra over a stated common band. Do not normalize away truncation changes.
2. Check mirror symmetry of this symmetric fixture, exact silence, finite state, nonnegative accumulated loss and the energy/work residual. These detect numerical regressions but do not calibrate the device.
3. Measure force-to-vibration and force-to-pressure transfer functions with an instrumented tap or swept shaker, both locally and across the actual target head. This identifies which external-air, shell, mount and cavity paths really exist.
4. Record controlled dry/wet rubbing and pull-off with synchronized normal/tangential force, speed, water quantity and both microphone channels. Fit physical parameters on one subset and assess held-out conditions. Examine force loops, modal frequency/decay, transfer phase, frequency-dependent interaural level/timing and uncertainty as well as listening.
5. Obtain geometry and material measurements before describing the fixture as a KU100 digital twin. Manufacturer microphone sensitivity can calibrate pressure-to-voltage for the device, but it cannot turn an invented chamber into that device's capsule pressure.

## Primary technical sources

- Bilbao, Torin & Chatziioannou, *Numerical Modeling of Collisions in Musical Instruments*, Acta Acustica (2015), [author manuscript](https://arxiv.org/abs/1405.2589), DOI [10.3813/AAA.918813](https://doi.org/10.3813/AAA.918813): energy-based collision potentials and discretization.
- Zheng & James, *Toward High-Quality Modal Contact Sound*, SIGGRAPH (2011), [author project](https://www.cs.cornell.edu/projects/Sound/mc/): contact must include vibrating-body feedback to capture micro-collisions and energy exchange.
- Chadwick, An & James, *Harmonic Shells* (2009), [author paper](https://www.cs.cornell.edu/projects/HarmonicShells/HarmonicShells09.pdf): mass-normalized structural reduction and limitations of modal truncation/radiation approximations.
- Matusiak, Chatziioannou & Van Walstijn (2025), [primary article](https://www.frontiersin.org/journals/signal-processing/articles/10.3389/frsip.2025.1525044/full): classic bristle friction is not automatically passive; its refined model and numerical solver have explicit assumptions and limitations. The native baseline uses the simpler dissipative law described above.
- Skotheim & Mahadevan, *Soft Lubrication* (2004), [author paper](https://softmath.seas.harvard.edu/wp-content/uploads/2019/10/2004-16.pdf): fluid films and compliance must be coupled for their actual geometry. It does not validate the native fixture's lumped film approximation.
- Wang et al., *Toward Wave-based Sound Synthesis for Computer Animation* (2018), [author paper](https://graphics.stanford.edu/projects/wavesolver/assets/wavesolver2018_opt.pdf): surface-acceleration boundary conditions and the effect of acoustic spatial discretization. The present fixture is much more reduced.
- [Abaqus coupled acoustic–structural theory](https://abaqus.uclouvain.be/English/SIMACAETHERefMap/simathe-c-acouststruct.htm): paired structural pressure traction and acoustic boundary motion.
- [Neumann KU100 product specifications](https://www.neumann.com/en-us/products/microphones/ku-100/): actual microphone characteristics, not the fixture's structural or internal acoustic parameters.
