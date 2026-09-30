# Object, material and action engine rebuild

Research date: 30 September 2026. Audited baseline: `c4ef705ca0924c24915a445e1b40a5efc83dcf68`.
Status: research and proposed implementation contract. No new renderer, binary dataset acquisition, listening result or deployment is claimed by this document. The [dataset registry](../../research/engine-rebuild/datasets.json) records inspection and licensing boundaries.

## Decision

Build a data-assisted physical engine with separate geometry, material, surface, contact, vibration, radiation and capture components. Keep a distinctly labeled learned acoustic-detail path where measurements reveal unresolved texture. Do not describe either a microphone-response preset bank or a general audio generator as a calibrated force-to-pressure solver.

Retain the current three object examples, native solver and reference-fitted ear texture as versioned baselines. The original wet tongue/artificial-ear problem remains a separate acceptance track; adding rigid-object taps is not its solution.

The near-term product has two layers: more identified object profiles for useful listening demonstrations, and a geometry-aware engine for interventions such as contact-point, material, tool and support changes. Their validation labels must remain distinct.

## Current implementation

The audited `ku100sim/modal_object.py` fits decaying sinusoids to one normalized measured response. Its output coefficients combine local vibration, mounting, radiation and recording response. The acquisition script hard-codes three objects and four rows. Stored parameters are not recording buffers, but neither are they separately identified bulk materials or a spatial sound field. The documented model flags reject an absolute force-to-pressure interpretation. [R1-R3]

Adding another JSON file currently adds an effective object-at-a-measurement-condition response. A material change cannot be reduced to changing its display name. Existing non-fitting-position checks are development diagnostics, not a blind generalization benchmark. Preserve their failures and source version.

## Dataset priorities

Counts are source-reported, not newly downloaded inventory.

| Priority | Resource | Role | Principal limitation |
|---|---|---|---|
| A | RealImpact: 50 objects, 150,000 measurements | Extend object coverage and identify contact/receiver dependence | Existing project subset lacks raw force streams referenced by the paper [S1] |
| A | ObjectFolder-Real: 100 physical objects | Mesh-aligned impacts with force profiles, 30-50 points per object | Physical objects overlap with RealImpact; reconcile identities before splitting [S2] |
| A | Cluster: 118 surfaces, 18,880 trials | Controlled sliding at five speeds, eight directions and two loads | Rubber probe; machine-reference microphone is not a second ear [S3] |
| B | Bare-finger tactile/audio/visual dataset | Human contact and motion/force relationships | 12.5 kHz audio does not validate the upper audio band [S4] |
| B | Hearing Hands | Hand-trajectory-conditioned source generation | Published model downsamples audio to 16 kHz; not full-band ASMR or force calibration [S5] |
| B | ObjectFolder 2.0 | Synthetic geometry/modal pretraining | Synthetic sound is not real-recording validation [S6] |
| C | NISR on Hugging Face | Candidate synthetic material/mesh/modal supervision | Author-card claims, coarse voxels, limited modes and no predefined split [S7] |
| C | FSD50K, SCHAEFFER, EPIC-SOUNDS | Labels, temporal structure and perceptual target diversity | Not controlled force/geometry calibration; processing and licenses vary [S8-S10] |
| C | 6KSFx | Procedural comparison baselines | Synthetic benchmark, not reality ground truth [S11] |
| C | KleinPAT | Radiation-precomputation reference | Far-field transfer is not a near-ear contact solution [S12] |

### Measurement traps

Cluster's force converter is 80 Hz although values are transported/logged much faster. Keep raw main/noise-reference channels separate from noise-cancelled mono. A high row count does not create high-bandwidth force supervision. The recorded speed/load grid bounds demonstrated conditions. [S3]

The bare-finger study excludes surfaces that impede smooth sliding. Treat this as action-selection bias, not evidence that irregular stick-slip is irrelevant. Its two microphones and acceleration are useful, but recording sample rate bounds the frequencies we may validate. [S4]

NISR derives geometry from ObjectFolder-Real and ObjectFolder 2.0; it does not supply 1,100 independently measured sounding objects. Synthetic material interpolation is not a validated composite-material constitutive law. Admit it only after several modal files reproduce in an independent solver and upstream rights are checked. [S7]

Do not merge recordings, force-corrected responses, noise-cancelled signals, reverberant audio, synthetic modal output and caption-only samples into one untyped waveform pool.

## Engine contracts

### ObjectAsset

Stable physical-object ID; dataset aliases; geometry hash; mesh units/scale; shell thickness where applicable; mass/volume if available; material model; support/grip; contact surface; action domain; backend; uncertainty; evidence version.

A visual surface mesh is not automatically a valid finite-element solid. Compilation diagnoses disconnected fragments, unresolved thickness, nonmanifold regions and unsupported elements. Unknown geometry or units prevent a physical-calibration label.

### MaterialModel and SurfaceModel

Bulk density, elasticity, damping and deformation regime are separate from surface topography and contact-pair friction. Use constitutive-model families, not a universal scalar hardness. Direction-dependent elasticity and frequency-dependent damping should be representable before every material family is implemented.

Each parameter has units, provenance and status: `measured`, `identified`, `literature_prior`, or `artistic`. Out-of-domain interventions remain visibly extrapolative. Optical/PBR roughness is not automatically a measured height spectrum. Acoustic absorption of a room surface is also a different property from an object's elastic stiffness.

### ContactPair and GestureState

Identify both contacting bodies, coordinates, normals, tool radius/compliance and supported action. A controller supplies a trajectory or load target, not a sound clip. State retains indentation, tangential displacement, stick/slip state, accumulated sliding and contact/release history. Fluid/adhesive state belongs only to a backend that implements it.

Progress from impacts to continuous sliding/rolling, then bristles, sheets and porous-liquid models. Never silently substitute faster taps for an unsupported continuous action.

### Vibration and radiation

A reduced elastic object uses:

```
M_r q_ddot + D_r q_dot + K_r q = B_r(contact_position, direction) F_contact(t)
```

Store surface mode shapes, not only resonance frequencies. Keep the contact excitation map separate from the listener output map. Use feedback between contacting bodies where the selected model requires it. Track support/radiation losses without double counting. Impact research motivates this separation. [S1,S13,S14]

An offline compiler produces verified reduced models. The native block renderer advances state and exports source audio, physical traces where defined, receiver settings and an auditable manifest. A diagnostic modal coordinate is not automatically pressure in pascals.

### Learned acoustic detail

An optional conditional generator uses speed/load/contact state and object descriptors for unresolved detail. Require fresh output, event timing, and appropriate stopping/decay. Log its contribution separately; do not let it silently compensate for a broken physical model.

Hearing Hands and physics-driven diffusion motivate action-conditioned learning, not physical certification. Hearing Hands processes audio at 16 kHz; upsampling does not restore measured detail above 8 kHz. Label the optional path `hybrid_physics_learned`, not pure simulation. [S5,S15]

### Receiver and capture domains

Use typed signals:

- `effective_microphone_response`: existing fitted object models, kept as legacy previews.
- `surface_motion`: structural motion awaiting radiation.
- `emitted_field`: a defined source representation and normalization.
- `capsule_pressure_pa`: known pressure at the two capsules.
- `digital_uncalibrated`: learned/statistical audio without pressure calibration.

Do not automatically filter an already microphone-colored signal through another microphone response. KU100 and 3Dio require their own rig identities and calibration. Airborne receiver data do not establish direct artificial-ear contact transmission. Keep useful learned timbre without assigning it unsupported Pa/N units.

## Identification strategy

Fit multiple experiments jointly. Estimate common resonant poles, then contact-dependent excitation and receiver-dependent output maps. Treat support and capture settings as nuisance variables rather than bulk material. Compare modal-only and residual-enabled candidates before retaining a stochastic component. [S14,S16]

For fixed isotropic geometry and Poisson ratio, `K = E K0` and `M = rho M0`; eigenfrequencies constrain `E/rho`. Scaling both E and rho equally leaves that ratio unchanged. Consequently a normalized tap cannot independently determine both. Measure mass and reliable volume/shape, or report an effective ratio. DiffSound explicitly estimates this ratio. [S13]

Require mesh refinement and independent eigenproblem residuals before audio fitting: otherwise material values can compensate for numerical error. Match nearly degenerate modes as subspaces rather than unstable frequency indices. Use measured forces when present; retain relative units when only processed responses are available. Never invent absent force arrays.

## Papers to turn into experiments

| Reference | Adopt/test | Do not infer |
|---|---|---|
| DiffSound [S13] | Offline high-order-FEM geometry/material-ratio fitting | Every material parameter is uniquely recoverable from one recording |
| DiffImpact [S14] | Joint impact excitation and resonance identification | A complete geometry/listener sound field |
| Audio-Material Reconstruction [S16] | Separate damping from support/capture confounds | A gripped mug's decay equals intrinsic ceramic damping |
| NeuralSound and KleinPAT [S17,S12] | Warm-start modal solves, precompute radiation | Far-field predictions work inside an occluded ear |
| Precomputed Acceleration Noise [S18] | Test rigid-body transient radiation | Arbitrary hiss represents physical acceleration radiation |
| Scraping/rolling model [S19] | Position-dependent continuous excitation | Sliding is identical impact playback |
| Differentiable nonlinear modal simulation [S20] | Inverse tests for nonlinear plates/membranes | A plate benchmark establishes wet silicone realism |
| Crumpling Sound Synthesis [S21] | State-dependent buckling and local vibrations | Static modal banks handle every folded sheet |
| Harmonic Fluids [S22] | Appropriate fluid/bubble/radiation mechanisms | Every mouth click is a bubble or saliva is just water |
| AcoustiTrace [S23] | Causal/intervention-based evaluation | A plausible soundtrack proves physics |

## Data and asset pipeline

Replace hardcoded IDs with an allowlisted registry. Reconcile physical object identities before grouping data. Download a bounded pilot, inspect actual arrays and rights, hash and cache outside Git. The current compressed-NPY prefix reader is useful for early rows, not repeated arbitrary access across the release. Convert approved records to per-trial/chunked storage once. [R3]

Separate immutable raw records from preprocessing derivatives. Store exact channel semantics, sensor rate/bandwidth, timestamps, geometry transforms, filters, gains, support and group IDs. Keep rejected/silent trials with explicit reasons; never silently replace missing measurements with zero arrays.

Proposed first pilot: 12-20 objects with several geometries within material classes, plus a bounded surface/friction set. This is a development budget, not a verified new library or a power calculation. Reserve whole physical objects and conditions before fitting.

Treat unresolved dataset/model/mesh terms as a production release blocker pending review. Source-code, waveform, annotation, mesh and trained-model rights are separate. FSD50K has per-clip terms; EPIC-SOUNDS states noncommercial terms; synthetic derivatives do not erase source mesh terms. These are source declarations, not a legal conclusion. [S6-S10]

## Migration and acceptance

| Stage | Implementation | Exit evidence |
|---|---|---|
| 0 | Freeze existing native, object and ear-texture baselines | Existing hashes and no-recording generation remain valid |
| 1 | Object registry, adapters, cache and grouped splits | Every pilot record has audited units/channels/provenance/rights |
| 2 | Multi-record identification and separate contact/output maps | Uninspected hit-point and capture-condition comparisons |
| 3 | Native causal, stateful block rendering | Independent numerical tests and predicted control interventions |
| 4 | Geometry compilation and measurement-refined materials | Mesh convergence and held-out object/geometry tests |
| 5 | Continuous friction and action models | Stop/reverse/speed/load tests against matched recordings |
| Parallel | Original wet-ear contact/seal/release research | Original handoff's timbre, gesture and bilateral acceptance |
| Later | Bristles, buckling, porous materials and liquids | Family-specific evidence and listening acceptance |

Keep Python/PyTorch offline for fitting; isolate optional JAX research. Retain C++ for compiled runtime models. Rust can later wrap jobs/assets, but changing languages is not the present sound-quality bottleneck. Validate neural preprocessing accelerators against numerical references. [S17,S20]

## Tests that matter

Keep numerical correctness, matched-recording prediction, listening acceptance and delivery status separate.

Numerical checks: excitation work, free-decay energy, finite output, applicable passivity, mesh/time convergence, anti-aliasing, zero excitation and reproducibility. Under-excited frequency bands remain unassessed. Choose mode count from the required bandwidth and convergence, not a universal fixed 24.

Causal checks: change hit position with force/listener fixed; change pulse duration without playback-speed edits; change support separately from material; stop/reverse a scrape; test simultaneous contacts and state continuity. Synthetic material swaps receive numerical tests distinct from real-recording validation.

Split by physical object, trial, support, force/tool condition, receiver position and session. Reconcile RealImpact/ObjectFolder identity and synthetic descendants. Splitting adjacent windows from a ringdown or duplicate mesh across training/test does not test generalization.

Listening: named reference/baseline/candidate playback first, optional blinding afterward. Test object/action identity, attack/detail, artifacts and continuity separately from near-ear presentation and ASMR feeling. Source-only and stereo comparisons both matter. Calibrated-level and level-matched timbre tests answer different questions. A single embedding score or waveform match cannot certify realism. [S23]

## Minimum custom recording

Use existing datasets first, rather than deferring all work pending a new rig. Where parameters remain ambiguous, capture repeatable impacts with known mesh locations, support, force and capture. Gentle fingers/tools require their own examples; hammer excitation does not identify every tool.

For the original wet-ear track, distinguish dry/wet, contact/no-contact, hold/slide/release, seal and capture settings. Record bilateral audio and only the additional observations needed to separate mechanisms. Do not infer saliva breakup from a filename. Sample counts and operating ranges must be chosen for identification, not advertised as a powered listener study.

## Delivery

Raw corpora and large renders belong in appropriately licensed dataset storage, not Git. Git holds code, compact models, source hashes and evaluation manifests. Cache compilation by geometry/material/solver hash; run small regressions for changes and full sweeps on demand. Documentation-only research should not regenerate all existing 30-second examples.

The viewer shows object, action, backend, validation domain and source version. Editing parameters triggers a real render or explicitly waits for one. Publish tested generated output only; keep private or unlicensed references local. Do not display invented physical traces for statistical audio.

## Primary sources and audited code

R1. Modal implementation: https://github.com/parafieldai/Ku100-Sim/blob/c4ef705ca0924c24915a445e1b40a5efc83dcf68/ku100sim/modal_object.py
R2. Object experiment: https://github.com/parafieldai/Ku100-Sim/blob/c4ef705ca0924c24915a445e1b40a5efc83dcf68/docs/objects/RESEARCH.md
R3. Acquisition: https://github.com/parafieldai/Ku100-Sim/blob/c4ef705ca0924c24915a445e1b40a5efc83dcf68/scripts/acquire_impact_subset.py
S1. RealImpact, CVPR 2023: https://arxiv.org/html/2306.09944v1
S2. ObjectFolder-Real: https://objectfolder.stanford.edu/objectfolder-real-download
S3. Cluster: https://arxiv.org/html/2407.16206 ; https://doi.org/10.1038/s41597-026-06760-z
S4. Bare-finger dataset: https://pmc.ncbi.nlm.nih.gov/articles/PMC11930942/
S5. Hearing Hands, CVPR 2025: https://arxiv.org/html/2506.09989v1
S6. ObjectFolder 2.0: https://objectfolder.stanford.edu/objectfolder2-0-download
S7. NISR author dataset card: https://huggingface.co/datasets/BumsooKim00/nisr-dataset
S8. FSD50K: https://zenodo.org/records/4060432
S9. SCHAEFFER: https://huggingface.co/datasets/dbschaeffer/SCHAEFFER
S10. EPIC-SOUNDS: https://github.com/epic-kitchens/epic-sounds-annotations
S11. 6KSFx: https://arxiv.org/abs/2501.17198
S12. KleinPAT: https://graphics.stanford.edu/projects/kleinpat/
S13. DiffSound: https://arxiv.org/html/2409.13486v1
S14. DiffImpact: https://proceedings.mlr.press/v164/clarke22a.html
S15. Physics-Driven Diffusion: https://arxiv.org/abs/2303.16897
S16. Audio-Material Reconstruction: https://pubmed.ncbi.nlm.nih.gov/30762560/
S17. NeuralSound: https://hellojxt.github.io/NeuralSound/
S18. Precomputed Acceleration Noise: https://www.cs.cornell.edu/projects/Sound/impact/
S19. Scraping and rolling model: https://arxiv.org/abs/2112.08984
S20. Differentiable nonlinear modal simulation: https://arxiv.org/abs/2505.05940
S21. Crumpling Sound Synthesis: https://research.adobe.com/publication/crumpling-sound-synthesis/
S22. Harmonic Fluids: https://www.cs.cornell.edu/projects/HarmonicFluids/
S23. AcoustiTrace, 2026 preprint: https://arxiv.org/html/2608.02035v2

Inspection boundary: primary papers, author descriptions, dataset cards, release listings and current project code were inspected. No new binary corpus or external model was downloaded, trained or executed in this pass. Existing three-object evidence belongs to the earlier named commit. Proposed dependencies require individual license, implementation and compute checks before adoption.
