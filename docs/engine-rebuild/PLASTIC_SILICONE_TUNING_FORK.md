# New source families: plastic, soft silicone and tuning forks

Research date: 2026-09-30. This narrows the earlier rebuild plan to the user's actual next objects. More wood, ceramic and glass tapping is not the requested expansion.

Status: primary-source and recording-metadata research plus proposed implementation/acceptance contracts. This document does not add a working sound model, training run, listening result or deployed preview. No new source recording or material-data ZIP was acquired successfully in this pass. Existing main audio remains unchanged. "Soft silicon" is interpreted as silicone rubber; "frequency fork" is interpreted as tuning fork.

## Separate material, object and action

The same material label can cover different source mechanisms. Use a material/object/contact/action tuple, not one plastic or silicone sound preset.

| Proposed object/action | Source model to implement | Primary comparison |
|---|---|---|
| Rigid plastic bowl: tap then damp | Identified modal response with tool/support dependence | Short attack, resonant coloration and damping |
| Thin plastic wrapper: squeeze/unfold | Deforming shell, snap-through events, self-contact/friction | Non-repeating crinkle clusters following the gesture |
| PET bottle wall: squeeze/release | Geometrically nonlinear shell, crease history, optional cavity coupling | Changes between loading, buckling, holding and release |
| Silicone pad: rub/stop/reverse | Finite-deformation viscoelastic contact with friction state | Surface-specific contact texture and event timing |
| Silicone dome: invert and return | Nonlinear snap-through shell with damping | Separate forward/reverse events from actual state changes |
| Silicone suction geometry: press/hold/peel | Deformation, sealing/leakage, pressure relaxation and opening | Contact/release signature; quiet holds where appropriate |
| Tuning fork: strike, ring, rotate, damp | Fork structural modes plus direction- and distance-dependent radiation | Attack, tone/decay and rotation-dependent level changes |

Descriptions are listening targets, not guaranteed sounds or new measured results. A dry silicone pad need not generate an audible squish under smooth compression. Extra contact, slip, cavities or fluid mechanisms must be supported rather than added because an object is called soft.

## Plastic

### Immediate measured rigid-plastic inputs

The RealImpact authors' object inventory includes `48_PlasticBowl`, `49_PlasticBowl`, `50_PlasticBowl`, `73_PlasticBin` and `97_PlasticScoop` [P1]. Their names establish object leads, not exact resin grades or new locally acquired records. Existing acquisition/fitting can be generalized for these impacts, while retaining its processed-microphone-response limitations.

This is the low-cost extension, but cannot establish bottle squeezing or bag crinkling. Tapping is only one action family.

### Deformation is the meaningful new backend

Crumpling Sound Synthesis models discrete buckling events and changing shell vibration, including unresolved small events [P2]. Use that structure to investigate wrapper/bottle sources; do not imitate a wrapper by repeatedly firing the wood-tap model.

Proposed implementation:

1. Evolve shell deformation with thickness, boundary/grip conditions and contact.
2. Detect rapid energy release and configuration changes, retaining hysteresis or permanent creases where the material model supports them.
3. Excite local structural/radiating modes at those events. Resolve fine vibration separately from the slower gross hand motion and test the coupling for energy/aliasing artifacts.
4. Add surface-contact rubbing only while surfaces move against each other.
5. Compare an optional event-conditioned statistical detail layer with physical-only output. Never store event waveform fragments.

A 60 Hz animation stream alone must not determine audio event timing. An engineering approximation may interpolate event times and use audio-rate modal evolution, but must disclose what shell motions remain unresolved. Mode reuse must be tested as geometry changes.

### Real acoustic targets found

- Freesound `391500`, megashroom: contributor describes squeezing a two-litre PET bottle; listed 96 kHz, 24-bit mono, 19.114 s, CC0 [P3]. Useful attack/crumple target, not synchronized force/deformation calibration.
- Freesound `658613`, RavenWolfProds: deflated plastic packing pouches handled, pulled and squeezed; contributor reports a Neumann TLM 103; 48 kHz, 24-bit mono, 133.256 s, CC0 [P4]. Useful multi-event acoustic target; no logged trajectory.

These are creator descriptions inspected online, not listening judgments or byte-verified downloaded audio. Original waveforms may support fitting/validation with applicable rights; the generator remains parameter/state driven.

## Soft silicone

### Real material data, not another hard-object profile

Roels, Costa Cornella and Brancart's elastomer-characterization release contains tension, compression, relaxation and other tests for ten elastomers, including Ecoflex 00-20/30/50 and Dragon Skin 20/30 [S1,S2]. The paper supplies constitutive fits. These are useful deformation/relaxation inputs, not microphone recordings or identified audio-band damping for our target.

Begin with a named formulation and specimen geometry. Fit a finite-strain hyperelastic law jointly to compression and tension; add time dependence from relaxation/dynamic tests. The choice among Ogden, Mooney-Rivlin or simpler laws is determined by fit and stability, not a claim that one formula represents all silicone. Shore hardness alone does not identify all of these quantities [S1]. Do not extrapolate slow tests into 20 kHz damping without evidence.

### Three separate silicone experiments

**Dry rubbing.** PDMS experiments show stiffness and surface chemistry can change stick-slip patterns [S3]. Use these as mechanism evidence, not numerical force parameters for an unrelated finger/artificial-ear assembly. Retain tangential deformation and stick/slip state, direction changes and recent contact history. Stop motion to test whether excitation stops appropriately.

**Dome inversion.** Work on silicone morphing sheets and elastic poppers establishes geometry-dependent snapping and contact dynamics [S4,S5]. These are mechanical studies, not a validated acoustic model of a specific toy. Couple snap dynamics to air/structure radiation; do not implement a scheduled pop sample or assume a gas bubble bursts.

**Seal/peel.** The suction-cup literature models geometry, contact roughness and leakage [S6]. The cited study tests soft PVC, not our silicone: equations and experimental design are leads, while material and acoustic parameters must be identified separately. A prescribed inward motion, sealed volume, finite leak and opening can form an initial pressure experiment; pressure equalization and actual microphone capture remain distinct stages. A stationary hold need not produce continuous sound.

Wet rubbing requires separate fluid/interfacial state. More wetness does not justify a monotonic increase in squeaks or pops. The existing pleasant microphone-domain texture must not be relabeled as a calibrated silicone contact mechanism.

### Concrete acoustic lead

Freesound `812067`, CVLTIV8R, explicitly describes silicone, water and scrubbies, close Sennheiser capture and processing in Reaper; it is listed CC0 [S7]. This is unusually relevant as a wet-texture target, but it is a processed multi-item sound, not pure silicone or a known liquid-bridge/force experiment. Do not use it alone to infer the isolated material response.

No complete public synchronized silicone-formulation/force/deformation/raw-binaural corpus was verified in this focused search. Proceed using public mechanical data and declared acoustic targets; add a small paired recording experiment to resolve the missing contact-to-microphone relationship rather than waiting for an exhaustive corpus.

## Tuning fork

### Why it is a useful next target

A struck tuning fork has structured modes and a measurable free decay. A plain sine oscillator supplies a tone, not its full strike, higher-mode behavior, support coupling or radiation. Penn State's examples distinguish the fundamental, clang and other modes; COMSOL's 440 Hz example reports a higher balanced mode near 2800 Hz [T1,T2]. These frequencies are example-dependent, not one universal overtone table.

Implement structural/modal motion with an excitation determined by strike location, direction and duration. Use an independently checked fork geometry, or identify a reduced model from recorded ringdown and clearly retain its empirical status. A weighted fork is a different mass/geometry configuration, not a simple pitch shift of an unweighted waveform.

### Orientation is essential for the near-ear effect

Russell's measured near/far-field study finds a longitudinal-quadrupole description for the fundamental: rotating the fork near the ear produces four level maxima/minima, versus two at arm's length in the reported experiment [T3]. This is directly relevant to a close moving-fork demonstration.

A sinusoid with left/right pan omits interference between the radiating parts. Use a finite-size, frequency-dependent radiation approximation, validated against the reference pattern and measured near-field distances. A rigid far-field pattern must not be applied unchanged at a few centimetres. Then solve or measure interaction with the head/ear receiver. Existing point-source HRIR coverage must not be extrapolated to contact or smaller radii without validation.

Proposed controls: nominal tuning (e.g. 256/512 Hz test designs), real fork geometry or identified profile, strike point/impulse, mallet compliance, orientation, receiver trajectory and explicit damping contact. No special physiological or therapeutic frequency effect is assumed.

### Usable resources

- MathWorks supplies a structural modal/transient tuning-fork example and geometry workflow [T4]. It is a numerical reference; commercial software examples are not automatically redistributable project code.
- Freesound `220747`: creator reports a 440 Hz fork on a resonance box, microphone inside the box, anechoic room, 80.360 s at 48 kHz mono, CC0 [T5]. Useful for checking a box-coupled decay, not an unmounted fork's free-field radiation.
- Freesound `126352`: creator describes a 512 C fork struck and moved, 17.737 s stereo, CC BY 3.0 [T6]. Useful qualitative motion target; there is no tracked trajectory or calibrated head geometry.
- AudioSet lists 200 tuning-fork annotations, but its own small label-quality audit found only 5/10 correct [T7]. Treat it as a discovery list, not 200 guaranteed valid laboratory trials.

For initial development, tuning-fork structure/ringdown plus orientation is the best-constrained of these new source families. This is a prioritization judgment, not a promise of fidelity before implementation and recording comparison.

## Replacement milestone and acceptance matrix

The next listening set should explicitly differ from previous wood/glass taps:

| Milestone | Controlled comparison | Acceptance evidence |
|---|---|---|
| Fork ringdown | Soft vs harder strike, fixed geometry/receiver | Fundamental, higher-mode amplitude/decay and real attack comparison |
| Fork motion | Stationary vs rotated at fixed radius | Predicted angular pattern and timed acoustic changes, not just pan |
| Plastic wrapper | Squeeze, stop, unfold, repeat | Events follow deformation/history; no arbitrary repeated tick stream |
| PET bottle | Slow/fast squeeze with fixed grip and cap state | Snap timing, loading/unloading differences and recorded timbre |
| Silicone rubbing | Same pad, forward/stop/reverse | Contact texture, stick-slip where observed and quiet-state behavior |
| Silicone dome/seal | Separate inversion and peel tests | Mechanism-specific onset/release, not the same procedural pop |

Keep separate checks for numerical accuracy, physical behavior, recorded sound match and subjective ASMR quality. A model can pass one and fail another. Use source-only audio before spatial presentation; then test the complete stereo output. Compare physically calibrated levels where available, and label any level matching used only for timbre.

No new generated examples accompany this research note. The later implementation must show actual files with stable material/action names, not claim these entries are already sound presets. The original wet-ear acceptance track remains active; silicone work is relevant to it but does not by itself identify the source of the user's recordings.

## Sources

P1. RealImpact author object inventory: https://github.com/samuel-clarke/RealImpact/blob/main/dataset/object_names.txt
P2. Cirio et al., Crumpling Sound Synthesis (2016): https://research.adobe.com/publication/crumpling-sound-synthesis/
P3. PET bottle creator recording: https://freesound.org/people/megashroom/sounds/391500/
P4. Packing-pouch creator recording: https://freesound.org/people/RavenWolfProds/sounds/658613/
S1. Roels et al., A Standardized Framework for Elastomer Characterization in Soft Robotics: https://doi.org/10.1002/aisy.202500699
S2. Accompanying measurement release: https://zenodo.org/records/14983287
S3. Stick-Slip Friction of PDMS Surfaces for Bioinspired Adhesives (2016): https://doi.org/10.1021/acs.langmuir.6b00513
S4. Liu et al., Snap-induced morphing (2023): https://doi.org/10.1016/j.jmps.2022.105116
S5. Snap and Jump: How Elastic Shells Pop Out (2025), author institution and paper: https://resou.osaka-u.ac.jp/en/research/2025/20250610_2 ; https://doi.org/10.1002/adrr.202500041
S6. Tiwari and Persson, Physics of suction cups (2019): https://doi.org/10.1039/C9SM01679A
S7. Silicone/water/scrubbies creator recording: https://freesound.org/people/CVLTIV8R/sounds/812067/
T1. Penn State, Vibrational Modes of a Tuning Fork: https://www.acs.psu.edu/drussell/Demos/TuningFork/fork-modes.html
T2. COMSOL tuning-fork structural example: https://www.comsol.com/blogs/tuning-fork-application/
T3. Russell, On the sound field radiated by a tuning fork (2000): https://pure.psu.edu/en/publications/on-the-sound-field-radiated-by-a-tuning-fork/ ; https://doi.org/10.1119/1.1286661
T4. MathWorks modal/transient example: https://www.mathworks.com/help/pde/ug/structural-dynamics-of-tuning-fork.html
T5. Resonance-box fork creator recording: https://freesound.org/people/jmuehlhans/sounds/220747/
T6. Moving 512 C fork creator recording: https://freesound.org/people/ScottFerguson1/sounds/126352/
T7. AudioSet tuning-fork class and quality notice: https://research.google.com/audioset/dataset/tuning_fork.html

License statements above are source metadata, not a blanket production clearance. Review code, data, example geometry and recordings separately. The elastomer ZIP download attempt did not succeed in this environment; its contents here are described from the release metadata and paper, not a successful binary inspection. No source creator's audio has been published or used at runtime by this note.
