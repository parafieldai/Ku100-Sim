# Contact integration: a separate source-artifact diagnosis

This is post-integration research on application `9019b3f7c01b7d68914b93acef50c61e7a56ddbb`, not a change to the deployed contact solver. The kernel under test has SHA-256 `74f3a964245bf42af7e685b1d1cb523c5d42ab1762c22ed2c2499f40fdd1af5b`.

## Why this was tested

The five-second contact auditions are a connected geometric prototype. They have not passed source-timbre or pressure-like listening acceptance. The original 1.5-second stronger-contact diagnostic already failed the declared mesh criteria. A separate light-contact diagnostic also exposes substantial source sensitivity. Rather than calling that a property of silicone, this experiment isolates the numerical contact integration.

## Flat-plane analytical test

Place a smooth sphere of radius R above a perfectly flat stationary plane. Its center height is h=R-delta. The numerical model applies the radial compliant-layer pressure k*(R-d) inside the sphere footprint, where k=E/layer_thickness. The plane-normal force includes the radial normal's vertical component h/d.

Integrating over the complete contact disk, with radial coordinate s and d=sqrt(s*s+h*h):

```
F = integral_0^sqrt(R^2-h^2) 2*pi*s*k*(R-d)*h/d ds
  = 2*pi*k*h * integral_h^R (R-d) dd
  = pi*k*h*(R-h)^2.
```

Translation over this uniform infinite plane cannot change that force. Every test footprint lies inside the finite test plane. Any force change in this setup is numerical: there is no material roughness, friction, inertia, viscosity, audio or changing indentation.

For the default six-by-three-by-four body grid, R=9 mm and delta=0.7 mm, the current three-point surface rule gives approximately **12.62% force RMS error** and **18.72% peak-to-peak force variation**, relative to the exact force. Twelve points reduce those figures to **1.805% / 3.066%**; forty-eight points reduce them to **0.1964% / 0.3660%**. All grids, depths and results are retained in `static.json`.

This identifies a concrete numerical source of apparent surface bumpiness. It does not prove that this is the only reason the dynamic audition sounds wrong.

## Dynamic light-contact check: still not converged

The same light-contact development trajectory was simulated with three, twelve and forty-eight points per boundary triangle on each of two body meshes. Only the integration rule changes within a given mesh; material, force law, load targets, time step and the source measurement remain fixed. There is no fitted gain or waveform alignment.

| Surface points per triangle | Force difference between meshes, fingertip / thumb | Surface-flux difference |
|---|---:|---:|
| 3, deployed rule | 13.43% / 12.57% | 112.95% |
| 12, scratch variant | 6.43% / 5.22% | 89.08% |
| 48, scratch variant | 6.94% / 5.77% | 50.08% |

**Every row fails at least one declared 5% mesh criterion.** Denser contact quadrature helps a known integration error, but it does not by itself resolve geometry-dependent source prediction. The force trend is not monotonic. Ratios above 100% are possible for waveform differences; they are not perceptual ratings or percentages of an audible artifact.

The trajectory duration is 1.5 seconds at 96 kHz, not the complete five-second audition. The last knot is sampled from the longer motion and the shortened knots are interpolated again. Consequently this is not literally the first 1.5 seconds of the public waveform. This qualification also applies to the shortened trajectory used by `validate_hand_scene.py`.

The results do not establish full-band radiation, physical skin parameters, an identified pressure signal, or an ASMR response. A new hidden texture layer or loudness adjustment was not used to improve the scores.

## Reproduce without modifying the engine

```
python research/contact-quadrature/reproduce.py --out outputs/contact-static
python research/contact-quadrature/reproduce.py --out outputs/contact-dynamic --dynamic
```

Use fresh output folders. The dynamic option copies the exact pinned source and required local material parameters into a temporary working directory. Only that scratch C++ contact quadrature is changed. It compiles the variants with their own source hashes and checks that the repository kernel remains unchanged. The experiment can take several minutes and writes summaries, not a replacement website or waveform library.

Both commands' underlying static test and the six dynamic runs were executed locally; `static.json` and `dynamic.json` preserve the output. This extra research is not part of the earlier 236-test cloud count. No human listening or new LLM-subagent review was performed.

## Next code change to qualify

Integrate contact pressure over the evolving contact patch more accurately, with bounded-error quadrature and contact broad-phase acceleration, rather than assigning one material sound to a sparse set of numerical sample points. Refine body geometry and the radiation/source operator separately. Keep the negative reference comparisons and test both light and stronger contact. None of the scratch variants above is promoted as a finished fix. A water/air subsystem would not repair this contact integration error.
