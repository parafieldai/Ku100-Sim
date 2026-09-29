# Passive unsteady viscous tube model

This is a new option in the **main C++ renderer**, not the separate contact-coupon benchmark. Set `physics.unsteady_viscous_losses` to 1. The original setting 0 remains available for reproducible legacy comparisons. `scenes/unsteady-stroke-left.json` uses the new model with 256 modes per plate; the original five scenes retain their input parameters.

## What changed, and why

The original duct/vent series impedance was plug-flow inertance plus constant Poiseuille resistance. Oscillatory no-slip flow develops a frequency-dependent boundary layer; a constant resistance does not reproduce that solution. Positive-real recursive approximations with explicit energy bookkeeping are a useful time-domain approach. See Bilbao and Harrison, *JASA* 140, 728–740 (2016), DOI [10.1121/1.4959025](https://doi.org/10.1121/1.4959025). That paper supports the passive modeling methodology, not a claim that these dimensions describe a KU100.

For a rigid circular tube, our reference is the independent analytical no-slip solution

`Z(s) = (rho*length/A) * s * I0(a*sqrt(s/nu)) / I2(a*sqrt(s/nu))`.

Using the product expansion and recurrence of Bessel functions gives

`Z(s)/M = s + 8*nu/a^2 + 4*nu/a^2 * sum_n s/(s + nu*j_(2,n)^2/a^2)`.

Here `nu=mu/rho`, `M=rho*length/A`, and `j_(2,n)` are positive zeros of J2. The mathematical Bessel-function identities and zero conventions are described by [NIST DLMF chapter 10](https://dlmf.nist.gov/10). This expansion and its grouping are implemented directly, not fitted to recordings.

The first eight poles are retained individually. The next poles through index 8192 are grouped into 24 positive branches. Each grouped pole is the harmonic mean of its component squared zeros and its weight is four times the count. The remaining fast tail is positive added inertance. This preserves DC Poiseuille resistance and the low-frequency effective inertance of `4M/3`.

For each branch, `z'=lambda*(U-z)`. Stored energy is `R*z^2/(2*lambda)` and dissipated power is `R*(U-z)^2`. Midpoint integration adds every branch's energy and loss to the existing bilateral fixture's work identity. The source feels these loads; this is not an output equalizer.

## Validation and bounds

`python scripts/validate_viscous.py` compiles the actual native header and compares it against SciPy's modified Bessel functions, a separate mathematical formulation. The 20–20000 Hz grid uses 1001 frequencies at radii 0.5, 1, 3 and 10 mm. Acceptance limits are 0.03% complex-impedance error and 0.4% resistance error. Tests also cover positive coefficients, DC resistance, low-frequency inertia, coefficient regeneration from independent Bessel zeros, and driven/undriven discrete work balance.

**These frequency-domain bounds concern the continuous rational approximation.** They do not include temporal warping, duct mesh error, uncertain geometry, or microphone calibration. `quality_gate.py` separately evaluates actual coupled trajectories at refined time steps and mode counts.

Thermal wall losses, turbulence, deforming tube walls, a moving free liquid surface, adhesion and capillary breakup remain absent. The analytical solution is a circular rigid laminar-tube reference, not an acoustic recording. No equivalent change to human-perceived sound quality follows from its numerical agreement alone.
