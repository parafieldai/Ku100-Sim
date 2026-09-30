# One parameterized engine, shared mechanical components

Implemented 30 September 2026. This is the first executable shared-mechanics stage,
not completion of the earlier geometry/material, radiation or wet-contact plan.

## What changed

`SimulationEngine(scene)` in `ku100sim/unified.py` compiles a declared graph into
`native/unified/engine.cpp`. Every new scene uses the **same class and native
kernel**. Names, material labels and file names do not select algorithms. The
node/edge arrays, initial state, forcing and driver trajectories determine the
response. There are no `PlasticSimulator`, `SiliconeSimulator` or `ForkSimulator`
classes. Metadata-renaming, arbitrary graph-composition and streaming tests check
that this is more than a common facade over separately named sound generators.

This does **not** mean every acoustic mechanism reduces to a few scalar knobs.
A new physical phenomenon needs a shared element/constitutive law and evidence.
Once implemented, it can be composed into many objects without another object
renderer. Unknown controls (for example an unsupported `wetness`) are rejected.

The existing native fixture, fitted object responses, and statistical ear textures
are unchanged and stay available as comparison baselines. They have NOT all been
silently migrated into this new physical graph or relabeled as calibrated Pa.

## Public API and dynamic behavior

```python
import json
from ku100sim.unified import SimulationEngine

scene = json.load(open('scenes/unified/plastic-snap.json'))
with SimulationEngine(scene) as engine:
    result = engine.render()
    velocity = result['velocity']  # weighted surface-velocity proxy, NOT Pa
    trace = result['trace']        # actual coordinates, state, work and energy

# The same class supports incremental control, without resetting history:
with SimulationEngine(scene) as engine:
    block = engine.process(2048)
    # Optional displacement/force arrays: (2048, node_count), SI units.
    # They override this block's driver positions or applied forces.
    next_block = engine.process(2048)
```

The controls are genuinely used in the mechanical time stepping. Editing stiffness
changes the equations; it is not playback-rate manipulation. Maxwell memory,
velocities and nonlinear well state continue across blocks. No recordings or
learned source parameters enter these new demonstrations. The tests prohibit
Python recording/array reads during rendering after compilation, and the native
kernel has no file I/O. This is not a universal sandbox/anti-memorization claim.

Rendering and arbitrary parameter changes happen natively through Python/C++, not
in the browser. Pages plays actual precomputed output, displays saved state, and
exports edited JSON. The editor explicitly leaves existing playback unchanged;
claiming it has rerendered would be wrong. A future WASM or native-job interface can
call this same engine instead of maintaining a second browser physics model.

## Shared elements and units

Each reduced coordinate q is in metres, velocity in m/s, mass m in kg. Supported:

- Elastic potential V(q) = k2 q^2/2 + k4 q^4/4. k2 is N/m, k4 is N/m^3.
- Nonnegative viscous damping c in N s/m.
- One optional Maxwell memory arm per coordinate: stiffness kr, relaxation tau.
- Linear positive spring couplings between coordinates, assembled as a Laplacian.
- Bilateral kinematic springs or unilateral penalty contacts to a prescribed driver.
- Smoothly interpolated driver displacement and generalized external force.
- Optional spatial sinusoidal surface-height terms, advected by a travel trajectory.

For k2 < 0, k4 must be positive. The resulting double-well potential has two stable
configurations; an additive constant makes the minimum zero. Buckling-like snaps
occur as the driven state crosses a barrier. Events are NOT scheduled by a clip
player or a random click timer. This reduced potential is not a deformed thin-shell
mesh, a material damage law, or an implementation of the cited crumpling paper.

The Maxwell arm stores stretch r and follows r_dot = q_dot - r/tau. Its force is
kr*r, energy kr*r^2/2, and dissipation rate kr*r^2/tau. This supplies actual stateful
relaxation rather than a sound-decay envelope labeled silicone. It is not a fitted
finite-strain Ecoflex or Dragon Skin constitutive law.

Unilateral driver contact uses W(delta)=kd*max(delta,0)^2/2, delta=u-q. Detached
contact cannot pull. Tangential friction, adhesion, rolling, fluid, porosity,
leaking cavities and arbitrary deformed geometry are not implemented here.

## Numerical integration

For a step h, qbar=(q1+q0)/2, vbar=(q1-q0)/h, and v1=2*vbar-v0.
The polynomial force is evaluated with its discrete gradient:

```
g(q1,q0) = k2*(q1+q0)/2 + k4*(q1+q0)*(q1*q1+q0*q0)/4
```

This satisfies g*(q1-q0)=V(q1)-V(q0) algebraically. Contact uses the corresponding
potential divided difference, including transitions across zero gap. Maxwell
memory is eliminated analytically at the midpoint, then restored after the step.
The SPD Newton system includes graph coupling; failed convergence aborts the
render instead of clamping energy or hiding overload. A failed engine must be
recreated, because a block may have advanced before the error.

Total energy includes kinetic, polynomial, coupling, driver-spring, and Maxwell
storage. External work includes applied-force displacement AND work done by moving
the driver. The reported balance is E(t)-E(0)+dissipation-work. Negative work is
allowed when an actuator extracts energy. Balance accounting is not proof that the
chosen topology represents an actual object.

An optimization recognizes **uncoupled, entirely linear** graphs and computes an
exact first-order-hold matrix transition. This optimization is based only on graph
coefficients, never object identity. It avoids accumulated modal phase error during
long ringing. Three-point Gaussian quadrature checks work/loss for this linear path;
the balance is a numerical residual, not claimed symbolically exact integration
of those rates. Other supported graphs share the discrete-gradient kernel.

The compiler rejects negative mass/damping, unbounded negative-stiffness laws,
unknown fields, invalid coupling endpoints, unresolved roughness-advection rates,
nonfinite values, and graphs beyond a declared stiffness/time-resolution envelope.
That envelope is a preflight check, not a universal nonlinear bandwidth theorem.
The measured trajectory-refinement tests remain necessary.

## Seven data definitions, not seven implementations

| Scene | Shared components | Status |
|---|---|---|
| Fork-like 256 and 512 Hz | Two linear modes, prescribed strike | Unmeasured modal design; no fork mesh |
| Stronger-damped 512 Hz | Same definition, four times viscous damping | Parameter intervention, not EQ |
| Plastic-like snap/slow loading | Ten quartic double wells and moving springs | Reduced buckling-cell demonstration |
| Silicone-like texture sweep | Nonlinear elastic + relaxation + unilateral contacts + advected surface | Normal-contact demonstration, no tangential friction |
| Silicone-like smooth hold | Same contacts without surface texture | Quiet-control demonstration, not continuous “squish” |

All parameters are illustrative and dimensioned, not measured material grades.
Adding an object within the supported element set means adding/changing JSON.
The next geometry compiler should derive coefficients and mode shapes from an
identified geometry/material/support definition; this commit does not supply it.
A large deformation in a real silicone body cannot be justified from a reduced
coordinate's displacement limit alone.

The source-only previews use the weighted velocity sum, 35 Hz high-pass, explicit
per-family gain, anti-alias filtering and a short end fade. Both channels are the
same signal. They are NOT sound pressure or a simulation of the KU100 capture path.
The smooth hold deliberately keeps the same gain as the texture sweep and may be
very quiet. It is presented as a control, not normalized upward into false detail.

## Research support versus present scope

- Bilbao, Torin & Chatziioannou, *Numerical Modeling of Collisions in Musical
  Instruments* (2014), https://arxiv.org/abs/1405.2589 : energy-based nonlinear
  contact across multiple systems. The implemented polynomial/contact gradient is
  documented above; no claim of reproducing every instrument in that paper.
- COMSOL, linear viscoelasticity theory,
  https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_theory.06.029.html :
  Maxwell/SLS storage, relaxation and dissipation. This implementation is reduced
  and uncalibrated; slow mechanical tests alone do not identify audio-band loss.
- Cirio et al., *Crumpling Sound Synthesis* (2016),
  https://research.adobe.com/publication/crumpling-sound-synthesis/ : relates
  buckling events to changing shell vibration. Our fixed double-well cells test a
  reusable stateful primitive, NOT their geometric buckling/radiation algorithm.
- Russell, *On the sound field radiated by a tuning fork* (2000),
  https://pure.psu.edu/en/publications/on-the-sound-field-radiated-by-a-tuning-fork/ :
  near/far quadrupole radiation. That directional field is explicitly NOT in these
  source-only fork previews. Rotating stereo gain would not implement it.

No new real recording or mechanical dataset was downloaded or fitted in this
stage. Data fitting is the next way to identify the graph coefficients/topology,
not a pretext to imply these test definitions already have validated material sound.

## Validation and migration gates

`tests/test_unified.py` checks closed-form damped motion, an independent DOP853
relaxation solution, coupling reciprocity, contact crossing, energy accounting,
zero input, live-control behavior, block-size invariance, forbidden controls,
no-recording rendering, and name-independent object composition.

`validate_unified.py` reruns four full six-second trajectories at double internal
rate. The fixed numerical velocity-norm limit is 1%; energy-balance tolerance is
1e-6 relative to initial energy and net actuator work magnitude. Quiet release and
three state transitions per plastic cell are checked. This does not establish
spatial convergence, parameter identifiability, recorded timbre, or ASMR quality.

Browser checks verify generated-file hashes, exact decoded audio, real playback,
seeking, original downloads, edited JSON, and the explicit no-fake-rerender rule.
The old site keeps its 80 MiB limit; this allowlisted extension has its own 24 MiB
maximum, with a combined 104 MiB ceiling. The cap increase is a delivery budget,
not a relaxed scientific threshold. Existing generated audio remains unchanged.

## Reproduce

Linux, C++17 compiler, existing NumPy/SciPy dependencies:

```bash
python -m unittest tests.test_unified -v
python scripts/validate_unified.py
python scripts/render_unified.py scenes/unified/plastic-snap.json \
  --out outputs/plastic-new --gain 12 --stiffness-scale 1.2
python scripts/build_unified_examples.py
# After existing generation prerequisites:
python scripts/package_unified_site.py
node scripts/browser_unified.mjs
```

Output paths must be new. The WAV, resolved scene, physical-state CSV and report
are saved together. The source hash identifies the exact native kernel. Source
code compilation is cached by hash; no arbitrary remote scripts or audio assets
are executed/loaded to render a scene.

## Local execution receipt before cloud validation

The 28 new native/Python regression tests and existing 25 frontend tests passed.
Independent six-second 192-to-384 kHz comparisons gave velocity-norm differences
of 0.00185% (fork), 0.13382% (snap cells), 0.01733% (textured normal contact) and
0.00237% (smooth contact), within the declared 1% limit. None is a realism score.
The local browser's ordinary HTTP navigation was blocked by administrator policy,
after the request client verified asset hashes. Browser/Pages success must therefore
come from the actual cloud test, not this local attempt. No browser policy was
changed. The legacy script-import issue caught by the new publication tests was
fixed without changing any physics or acceptance tolerance.
