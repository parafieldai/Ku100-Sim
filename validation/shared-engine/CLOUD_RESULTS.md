# Shared mechanical engine: executed pre-integration evidence

Date: 30 September 2026. This is the first reduced-coordinate implementation,
not measured plastic/silicone calibration or full fork acoustics. See
[the implementation contract](../../docs/engine-rebuild/UNIFIED_ENGINE.md).

## Exact source

[Validation run 36751828671](https://github.com/parafieldai/Ku100-Sim/actions/runs/36751828671)
completed successfully. The expanded, tested source tree is
`a56e4858dcf7c930c904b9497072e8b9451803e6`. All 25 changed files' byte counts,
SHA-256 values and Git blob IDs were checked against the locally tested source.
The authorized connector assembled that exact tree, removing the temporary
source transport files and apply workflow. No force push was used.

Artifact `shared-engine-36751828671`, ID `11114648586`, contains the exact source,
logs, seven generated examples, actual mechanical traces and browser screenshots.
Its 9,010,459 bytes have SHA-256:

```
b6839b17180687a108303590569ee42cc947ccf983f6e5c69eb028bdfb281606
```

The artifact was downloaded and every ZIP CRC passed. The earlier attempt
[36751599921](https://github.com/parafieldai/Ku100-Sim/actions/runs/36751599921)
failed before tests because combining the numerical and texture requirements
applied PyTorch's CPU package index to SciPy. The rerun installed the unchanged
requirements separately, as the normal main workflow already does. No numerical
tolerance or browser assertion was weakened.

## Executed tests

- 173 native/Python tests passed, zero skips/failures; 28 are new shared-core and
  publication tests. The old mechanical, measured-object and texture tests remain.
- 25 frontend tests passed, zero skips/failures.
- Four six-second temporal-refinement comparisons passed the fixed 1% velocity-
  norm limit. The energy-balance limit remains 1e-6 relative to initial energy
  plus the magnitude of net actuator work.
- Chromium 151.0.7922.34 verified all 25 shared-page assets against exact hashes
  and all seven 48 kHz stereo WAVs against decoded samples. It exercised real
  playback, completed seeking, unchanged downloads, edited-scene export and the
  explicit rule that parameter editing does not silently alter precomputed audio.
- Desktop and mobile layouts passed; no application errors were recorded. The
  existing source-texture browser suite also passed after its navigation update.

| Six-second scene | 192 to 384 kHz velocity relative L2 |
|---|---:|
| Fork-like 512 Hz | 0.00185% |
| Bistable plastic-like cells | 0.13382% |
| Silicone-like normal texture sweep | 0.01733% |
| Smooth normal-contact hold | 0.00237% |

These are time-discretization comparisons, not perceptual or material-accuracy
scores. There is no spatial-geometry convergence claim. All seven examples report
the same native kernel SHA-256:

```
75246326661f9c47f9ec90fba017494a89065a35b47887e5056fcacbd832eaa7
```

The tests independently check a closed-form damped oscillator, a DOP853 solution
of nonlinear elastic/relaxing motion, spring-coupling reciprocity, contact work,
energy accounting, block-size invariance, live force input, and rejection of
unsupported parameters. Renaming the scene leaves the trajectory unchanged;
composing linear/nonlinear/relaxing nodes does not require a new object class.

## Research and delivery distinction

The preceding rebuild plan, plastic/silicone/fork research and dataset registry
are integrated alongside this source without changing their historical status.
They are research specifications, not evidence that all their mechanisms are now
implemented. The four extra documentation/registry files added after the tested
tree do not modify the native equations, scenes, rendering or viewer code.

The default inputs are illustrative SI-valued reduced parameters. No source
recording was fitted or replayed to create the seven examples. The listening
readout is weighted structural velocity with a declared shared per-family gain,
not pressure in Pa or a KU100/3Dio recording. Snap-through uses reduced double-well
cells, not a resolved plastic shell. Normal silicone contact retains relaxation
state but does not solve tangential stick-slip, liquid bridges or sealing. The
fork demonstration omits geometry-dependent directional radiation.

Existing native, statistical ear-texture and measured object renderers are kept
as legacy baselines, not silently converted to this new engine. No human listening
assessment or newly spawned LLM subagent audit was performed. A local sanitizer
exercise of four shared-kernel scenarios also passed, but is separate from the
cloud suite listed above.

The final main CI, Pages deployment and live HTTPS verification must be checked
at the integration commit. This successful branch run tests HTTP on a GitHub
runner; it is not itself evidence that Pages has deployed.
