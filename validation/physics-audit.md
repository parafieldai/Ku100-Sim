# Independent physical-core and native CLI audit

The audited implementation passes **eight independent unittest methods with zero failures, errors or skips**. The tests found no remaining sign, unit, contact-work or structural/acoustic coupling discrepancy in the exercised cases. The source hashes, exact defaults, compiler identity and measured errors are in [physics-audit.json](physics-audit.json); the executed output is in [physics-audit-unittest.txt](physics-audit-unittest.txt). These results accompany the separate [receiver audit](receiver-audit.md).

This is evidence that the declared generic fixture is implemented consistently. It does not identify the fixture with a measured KU100, calibrate its source pressure against a microphone, or establish perceptual similarity to a recording.

Reproduce from the repository root:

```sh
python -m unittest discover -s tests -p test_physics_audit.py -v
```

The suite builds the complete native executable in a temporary directory and records its source identity. A second temporary test adapter exposes the physical equation helpers without changing their implementation or the public API. The independent calculations use spatial quadrature, LAPACK, SciPy root finding, and a dense state-space solve. No recorded performance, learned sound model, loudness target, or listening judgment enters these tests. Compilation produced no warnings.

At the recorded run, `native/physics.cpp` had SHA256 `ac154b7743d680ea064614d456fe6822cc836716478a8596c6cf31fb5509e961`; `native/main.cpp` had SHA256 `7a36b00635e5a22ca9160a62e73730e32e46ef8f9f55c5c93f4ecd2cc2cddd32`. The JSON includes all remaining source and wrapper hashes.

## Independent numerical checks

| Check | Independent method | Recorded result |
| --- | --- | --- |
| Mindlin eigenfrequencies and force/volume ports | Integrate kinetic, bending and shear energy of the spatial basis using Gauss–Legendre quadrature; solve the generalized eigenproblem with LAPACK; integrate the Gaussian footprint with Gauss–Hermite quadrature | Maximum eigenvalue relative error 4.44e−13; maximum absolute error in port outer products 5.43e−12 |
| Static reference compliance | Solve the physical static stiffness matrix directly for every harmonic in the complete 96×96 candidate space | Independent 0.015202399319284006 m/N; native 0.015202399319283834 m/N |
| Excitation under mode refinement | Request 1, 16 and 128 retained modes while checking the full-space reference compliance | Identical native reference compliance at all three counts |
| Normal contact discrete gradient | Independently integrate the continuous Hertz force along the indentation interval | Maximum force error 6.94e−18 N, including contact, release, zero contact and nearly equal positive endpoints |
| Coupled normal/tangential contact | Solve the two simultaneous nonlinear force equations with SciPy's root solver; include opening/closing, either slip sign and dry/wet cases | Maximum force error 6.36e−14 N; minimum dissipation power zero |
| Complete linear physical network | Assemble the original differential equations as a dense matrix, scale by stored energy, and apply implicit midpoint without the native elimination | Maximum chamber-pressure difference 2.56e−12 Pa; maximum stored-energy difference 1.42e−20 J |
| Native work balance in the dense-reference experiment | Compare independently reconstructed state energy and reported work/loss trace | Maximum native work-balance residual 3.31e−20 J |
| Capture controls | Render identical physics with preamp settings differing by 20 dB | Audio amplitude changes by ten; raw chamber/source WAV bytes and physical statistics remain identical |
| Airborne CLI path | Independently filter the selected right vent with a synthetic stereo bank and full fractional propagation delay | Relative waveform error 3.44e−8 after accounting for the raw source's float32 export |
| Trace/audio timing | Match the first physical sample and subsequent trace rows to the WAV grid; check the bundle's decimation latency | First physical sample at 1/192000 s maps to displayed time 64/48000 s in the tested decimated contact bundle |

The complete-network comparison uses 3 modes per plate, 3 duct cells, 48 kHz integration, a 50 ms stroke, 0.004 N nominal load, zero texture roughness, 0.4 wetness and 0.02 m/s tool speed. It compares every one of the 2,400 steps. This intentionally small fixture makes every internal network state available to the independent dense calculation; it tests the coupling algebra without presenting a low mode or cell count as a fidelity setting. The model's separate convergence experiments cover refinement of the production defaults.

## Signs, units and energy exchange

### Plate reduction and the three work ports

The independent plate test starts from the declared spatial displacement and rotation fields. It integrates the shear strains `w_x − theta_x` and `w_y − theta_y`, the bending curvatures, the mixed-curvature term and the rotational/translational kinetic energies. This checks the area factor, rotary mass, shear and bending contributions together. It does not merely compare the C++ matrix to a second copy of the same matrix literal.

The generalized eigenvectors are then projected into the normal, tangential and volume ports. A mode's arbitrary eigenvector sign cannot change a physical prediction, so the comparison uses all self and cross products of these three port coefficients. This explicitly checks the sign of the tangential surface displacement `−(h/2) theta_x` relative to normal displacement and volume motion. The test includes four harmonic/material configurations rather than just the lowest bending frequency.

With mass-normalized coordinates, modal displacement has units `sqrt(kg) m` and velocity has units `sqrt(kg) m/s`. The normal and tangential projections have units `1/sqrt(kg)`; multiplying by a force produces the required modal acceleration. The volume projection has units `m²/sqrt(kg)`, so its velocity product is a volume flow. Pressure times the same volume projection provides the equal and opposite structural force. The implementation uses these adjoint mappings consistently. The equations and parameter conventions are documented in [PHYSICS.md](../docs/PHYSICS.md).

### Contact and friction

The independent contact-force reference integrates `k max(delta,0)^(3/2)` along the interval between the two indentation endpoints. This verifies the native divided difference even when the contact opens or closes during a step. The force remains nonnegative and its interval work agrees with the change of the contact potential.

The normal and tangential forces are also compared with a simultaneous nonlinear solve that does not use the native nested iteration. The tested cases include negative slip, opening motion, a previously open contact that closes, and viscous film contributions. The native relative velocities, force coupling and nonnegative loss agree with this independent calculation.

This verifies the implemented smooth friction and viscous-film equations. It does not turn them into a model of static sticking, bristle energy, adhesion, cavitation or capillary rupture. The code does not have those states.

### Duct, chambers and radiation

The dense reference retains both plates, every pressure cell, each duct flow, both vent flows and both radiation states. Its matrix is assembled directly from volume conservation, pressure traction, inertance and resistance equations. The two end edges use half a duct cell; their total length plus the interior edges equals the declared duct length. The chamber volume is additional to the full volume of the duct cells.

The reference is driven by the native contact forces recorded at every step. This isolates the structural/acoustic evolution from the nonlinear contact solver, which is checked separately. Both chamber pressures, both radiated source observations and the entire stored energy match. The stored-energy comparison includes the contact potential evaluated from the recorded indentation. It is an independent check of the reported physical states and energy accounting, not an independently measured contact-force history.

For the radiation branch, `tau dz/dt = Q − z` and `p_rad = R(Q − z)` imply

```
p_rad Q = d(R tau z²/2)/dt + R(Q − z)².
```

The native radiation storage, dissipated power and observed source use this same sign convention. The dense comparison checks its integration together with the vent inertance and chamber feedback. This is a passive equivalent load; its sphere geometry remains an approximation to a vent's acoustic radiation.

## Corrections and output interpretation

The implementation owners corrected the trace/audio origin during this audit. Physical vector index zero is the end-of-step state at `dt`; WAV frame zero has playback time zero. The bundle must therefore use

```
displayed_audio_time = simulation_time − dt
                       + decimation_delay
                       + fractional_filter_delay
                       + modeled_flight_time.
```

The native report now records `simulation_first_sample_s`, and the bundle uses it when translating trace times. The test checks the identity-decimation case against every raw pressure sample and the 192-to-48 kHz case against the bundle trace. The HRIR bank's published time origin is preserved separately and is not presented as a measured absolute flight time.

The native CLI's default bank path is now `data/ku100_bank.bin`. The airborne test creates a synthetic bank at that default location and verifies selection of the right-side vent rather than a mixture of the two vents. The final output equals the independently computed propagation filter, per-ear bank convolution and one common capture gain. The full convolution tail is retained.

No hidden output normalization was found in the physical core or exercised CLI path. Changing capture gain leaves the raw pascal-valued chamber and source WAV files byte-identical. The deterministic texture's specified roughness amplitude is an input surface parameter; it is not a gain fitted to an output recording.

## Domain limits that remain material

The implementation owner reduced the initial 0.6 N nominal-load default to 0.01 N after checking model regimes. The independent static compliance above explains why that was necessary: the linear static plate contribution alone predicts approximately 9.12 mm at 0.6 N, more than three times the declared 3 mm thickness. At 0.01 N that contribution is approximately 0.152 mm, or 0.0507 thickness. These are predictions of the generic model, not material measurements. They must not be interpreted as a validation of a real silicone ear. Large-deflection plate models include additional membrane effects; for primary background, see the [NACA large-deflection plate analysis](https://ntrs.nasa.gov/citations/19930084864).

The current source reports a conservative global modal displacement bound, its ratio to plate thickness, vent/duct Mach and Reynolds numbers, and warnings when its chosen screening limits are exceeded. These diagnostics address concrete assumptions that an energy residual alone cannot test. A passing `regime_valid` flag only means those implemented screens passed. It does not establish a complete material, acoustic or device-validity domain.

Several limitations follow directly from the declared model and its observations:

- The plate geometry, material constants, chamber volumes, duct and vent geometry are generic inputs. No instrumented KU100 identification establishes these as its real force-to-pressure paths.
- Linear Mindlin plates omit geometric membrane nonlinearity and finite-strain material response. The current surface-traction model also omits a deformable fingertip and actual changing contact area.
- The one-dimensional duct, quasi-steady wall resistance and lumped chambers do not resolve all spatial or viscothermal effects. Stability and passivity cannot certify their bandwidth.
- The force law is smooth, dissipative friction with a limited viscous film. It lacks the fluid and adhesive state needed to claim physically validated wet-contact events.
- The tested native capture gain maps modeled pressure into digital samples under declared electrical settings. It does not calibrate the modeled chamber pressure to an actual KU100 capsule.
- The measured airborne receiver is a separate transfer path. Applying it to one modeled vent does not validate a contacting finger-to-ear path, internal head transmission, or the source model's spectrum.

The appropriate outcome is a numerically audited, physically accounted generic fixture with reproducible source identity and explicit limits. Force-synchronized material, vibration and bilateral pressure measurements are still required before claiming device fidelity or recording-level perceptual accuracy.
