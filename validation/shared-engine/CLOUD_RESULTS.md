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
fc45131e8494346abb22d17b4bd3d774c1eae517f7600e265cecc976595f4008
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

## Continuation verification and checksum correction

On 30 September 2026, the interrupted implementation was recovered from artifact
11114648586 again. Its complete archive SHA-256 and ZIP CRCs were verified. The
native source matches Git blob `b93fa38128ea93270f2630d9c8f16cca6582a077`, and the
Python API matches `895369c23026c2b2cbfc4a409aba93e4c449e310`, as read from main
at `9b93e73b9eaf6caa11d2fdd159bc2f7236b7d6d8`.

The earlier checksum text in this document was incorrectly
`75246326661f9c47f9ec90fba017494a89065a35b47887e5056fcacbd832eaa7`.
The corrected `fc45131e...` value above is independently computed from the
actual C++ source and agrees with all seven generated example manifests. This is
a documentation correction, not a renderer replacement.

In this continuation, all 28 shared-core/publication tests and the four full
six-second temporal-refinement comparisons were rerun successfully. All seven
example WAVs were freshly regenerated and are byte-identical to the hashes in
the deployed-site verification. The local environment was Python 3.13.5, NumPy
2.3.5 and SciPy 1.17.0. The previously recorded full 173-test cloud result is not
presented as a new local full-suite run.

The actual main CI 36752742618, Pages deployment 36754494993 and live verification
36754605646 were rechecked through GitHub. The downloaded live artifact 11115878353
matches SHA-256 `84013826bc79be84d8c9b9eb7bdf00f09b514dce5e42bc01f1beeb024e77835d`
and passes every ZIP CRC. Its report records 25 matched live assets and all seven
playback/seek/download checks. No new local-browser or human listening test is
claimed. The deployed application remains `f20ab7d`; this documentation-only
correction does not require regenerating or redeploying its audio.
