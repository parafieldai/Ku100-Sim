# Physical model and its domain

The native renderer generates a fresh waveform from a prescribed interaction; it does not decode a performance recording. It is a **coupled test-coupon surrogate**, not the full geometry or measured mechanics of a KU100 or 3Dio. The browser is an offline-output viewer, not the solver.

## State equations (SI units)

Let q and v be modal displacement and velocity for two simply supported, thin rectangular plates. A_L and A_R integrate each mode's displaced volume. The signed vector s maps displacement to an assumed inter-plate spring. Each side has cavity pressure p, vent volume flow U and a radiation-memory state z.

```
q_dot = v
M v_dot = -K q - D v - k_c s s^T q - A_L p_L - A_R p_R + g F
C p_dot = A^T v - U
M_vent U_dot = p - R_vent U - R_rad (U-z)
tau z_dot = U-z
```

The cavity acts back on the structure. Radiation acts back on the vent. This is not a feed-forward EQ/noise source. Parameters are in `src/sim.cpp` and are deliberately labeled assumptions.

Hertz-type contact uses potential `Phi(delta)=K_H max(delta,0)^(5/2)/(5/2)`. The moving, Gaussian spatial patch g samples the structure. The force includes a closing-only Newtonian squeeze-film approximation with a minimum assumed film thickness. It does **not** solve saliva transport, adhesion, filament breakup, bubbles, wet friction or tissue mechanics. Spatial texture is prescribed analytically, not measured.

## Energy accounting

Stored energy is the sum of modal kinetic/elastic energies, coupling-spring energy, cavity compression, vent inertia, radiation-memory energy, and contact potential. With linear midpoint steps and the discrete contact potential gradient:

```
E_new - E_old + material_loss + film_loss + vent_loss + radiation_loss = actuator_work
```

For moving contact, actuator work includes `F*(Delta actuation - q_mid^T Delta g)`. Omitting that geometric term would produce an incorrect balance. Every native step accumulates the actual work and losses. There is no corrective energy clamp. The lagged film coefficient is not a general second-order nonlinear integration method.

## Geometry and validity

Each assumed plate is 30 x 40 x 1 mm; Young modulus 1.2 MPa, Poisson ratio 0.49, density 1100 kg/m3. These are neither a KU100 ear mesh nor measured KU100 material constants. The plates use Kirchhoff-Love bending, **not Mindlin theory**. At high retained spatial frequencies, the thin-plate assumptions themselves become questionable; numerical modal convergence would not resolve that physical-model error.

The assumed cavity volume is 1 cm3. The ideal vent and equivalent spherical radiation load do not establish a dummy head's true internal structure. The default coupling is 1 N/m, uncalibrated. Its influence on the opposite channel is a sensitivity parameter, not a measured head-transmission path.

## Output and receivers

Contact output samples are modeled **pascals**, written as unnormalized Float32 WAV. They are not calibrated microphone volts or an ADC's dBFS. A sample above 1 Pa is not clipping. Preview files use one common documented gain for both ears. The preview gain is not a physics parameter.

The measured route applies a KU100 airborne FIR to the physically generated vent-radiation observation. It is separate from the local-cavity route. It does not apply another head shadow, ear canal or diffuse-field EQ after the measured response. Authors' distance factors are applied once during extraction. No absolute acoustic flight time or microphone pressure calibration is claimed for the processed measurements. The native FIR has full tails; anti-alias conversion to 48 kHz adds 1 ms latency. View telemetry is the source/cavity state, not a post-FIR microphone-pressure trace.

`tools/sphere.py` is a separate rigid-sphere Helmholtz benchmark with a point source outside an 8.75 cm radius sphere, not an anatomical ear solver. It solves a spherical-wave series, checks series refinement and static limits, and is compared against measured KU100 interaural levels without fitting. It is not used to overwrite the measured KU100 responses.
