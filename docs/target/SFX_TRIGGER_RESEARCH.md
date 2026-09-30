# Sound effects, items and triggers: source-first research

Checked 29 September 2026. Machine-readable inventory:
`research/target/triggers.json`. The comparison page displays the same entries.
The primary target remains nonverbal wet mouth/artificial-ear interaction. Other
items below are diagnostic materials or later extensions, **not implemented sound
presets and not substitutes for the primary investigation**.

## Separate four things

1. **Item/contact pair:** what is interacting, including material and geometry.
2. **Action:** tap, slide, roll, hold, peel, squeeze, crumple or release.
3. **Acoustic description:** attack, sustain, ending, pulse clusters, pitch/noise,
   spectral evolution, decay and quiet intervals. These are observable descriptors.
4. **Source and transfer hypothesis:** where the acoustic excitation originates,
   how it couples to the object/air, and how it reaches both microphones.

A browser button labelled “wetness” conflates these unless its state and acoustic
consequences are demonstrated. A sound named “pop” does not identify a bubble.
Google's [AudioSet surface-contact ontology](https://research.google.com/audioset/ontology/surface_contact_1.html)
separates scratch, scrape, rub and roll. Its [liquid ontology](https://research.google.com/audioset/ontology/liquid.html)
separates saturated-material squish from drip, pour and splash. These help label
observations; they do not supply physical parameters or validate this simulator.
[UCS](https://universalcategorysystem.com/) is useful for consistent SFX names and
categories, not a physics model or blanket license for sound assets.

## Ranked sources and platform findings

| Source | What was actually inspected | Useful relationship | Boundary |
|---|---|---|---|
| [RealImpact](https://samuelpclarke.com/realimpact/), Clarke et al., CVPR 2023 | Author project and recording setup | Impact force/location, object/material and microphone-position information in 150,000 recordings of 50 objects | No new trial downloaded in this pass; dry object impacts, not wet-ear contact |
| [Greatest Hits](https://andrewowens.com/vis/), Owens et al., 2016 | Author page and dataset/sample categories | Hitting/scratching gestures on different materials with video and sound | Its example-based synthesis is incompatible with the no-runtime-clip-retrieval requirement; not adopted |
| [FSD50K](https://zenodo.org/records/4060432), Fonseca et al. | Release metadata and primary dataset description | Broad SFX event/source labels; 51,197 clips, 200 classes | 44.1 kHz PCM16 mono, weak clip labels; no new audio downloaded, and per-clip licenses/no stereo contact calibration |
| [SCHAEFFER on HF](https://huggingface.co/datasets/dbschaeffer/SCHAEFFER), Berta & Ghisi, DAFx 2025 | Author repository, HF card and visible example rows | 1,000 sound objects with pulse/onset/sustain/offset/process annotations | Designed/processed sounds as well as recordings; not raw force-to-audio measurements |
| [SCHAEFFER on Kaggle](https://www.kaggle.com/datasets/maurizioberta/test-schaeffer) | Resolved the exact link supplied by the authors; readable content inspected on HF instead | A genuine author-linked audio dataset lead, unlike the prior channel-analytics result | Kaggle page did not return a readable data body here; no sample downloaded |
| [SonicGauss on HF](https://huggingface.co/datasets/AiEson2/SonicGauss/blob/main/README.md) | Dataset card | ObjectFolder-derived synthetic/real impact sounds and visual object assets | Preserve synthetic/real identity and original-source rights; not wet-ear data; no audio downloaded |
| [Cluster Haptic Texture Dataset](https://www.nature.com/articles/s41597-026-06760-z), Eguchi et al., 2026 | Primary descriptor and the previously retained paired-trial audit | Dry sliding motion/force/acceleration with raw and processed sound | Contact-plus-machine and machine-reference channels are not binaural ears; sensor logging rate is not physical sensor bandwidth |

SCHAEFFER's authors distribute its data/audio under CC BY 4.0 and code under a
separate GPL license. No GPL implementation was copied into this project. Its
visible HF rows explicitly include layering, granular processing, distortion and
filtering. A “raw file” in a curated sound-object corpus is therefore not evidence
of an unprocessed physical microphone trial. No recording from these newly
researched collections is a runtime asset in the new comparator.

## Mechanism evidence worth following, without inappropriate transfer

**Tape peel.** Li et al., [Screeching sound of peeling tape](https://journals.aps.org/pre/abstract/10.1103/p19h-9ysx),
Physical Review E 113, 025508 (2026), DOI 10.1103/p19h-9ysx. The inspected primary
abstract reports synchronized two-microphone/high-speed-imaging evidence linking
their tape pulses to transverse fracture tips reaching the tape edge. This is a
strong example of *how* to identify a sound source. It does not show that saliva
release uses that mechanism; no such equation or event generator is imported here.

**Sheet crackle.** Kramer & Lobkovsky, [Universal power law in the noise from a crumpled elastic sheet](https://journals.aps.org/pre/abstract/10.1103/PhysRevE.53.1465),
Physical Review E 53, 1465 (1996), DOI 10.1103/PhysRevE.53.1465. The primary abstract
describes recordings of discrete clicks during rapid changes in strained Mylar
configuration. This supports studying event/state history for crumpling, not using
a universal “crinkle noise” filter for paper, plastic and wet mouth contact alike.

**Measured binaural transfer.** The retained [KU100 near-field HRIR source](https://zenodo.org/records/4297951)
is useful for its measured airborne geometry. It does not establish what a tongue
touching/sealing an artificial ear injects mechanically or acoustically into the
microphone system. Do not spatialize already fitted microphone-domain recordings
again merely because the project name contains KU100.

## Proposed item/action matrix (not empirical results)

| Priority | Item/contact pair | Actions to distinguish | Main observation needed |
|---|---|---|---|
| Primary | Tongue/compliant surrogate + wetted artificial ear | Slide, reverse, roll, hold, peel, release | Same raw stereo capture with observed contact state/motion; force when needed to identify the chosen model |
| Control | Mouth near but not touching the ear | Non-contact mouth gesture | Discriminate internal-mouth emission from pinna contact |
| Diagnostic | Dry/wet silicone coupon + pad | Rub/stop/recontact | Formulation, topography, force, slip and transmission; not a presumed KU100 ear |
| Diagnostic | Adhesive tape + substrate | Slow/rapid peel | Peel geometry and synchronized force/imaging/audio |
| Later | Glass/ceramic, wood, metal or rigid plastic + specified tool | Tap at points, damp, flex, latch | Distinguish tool contact from structural modes and mechanism changes |
| Later | Brush + named surface | Brush, reverse, stop | Bristle/contact geometry and gross stroke state |
| Later | Paper/Mylar/plastic sheet | Fold, crumple, unfold | State/history and discrete configuration events |
| Later | Cloth or leather-like material | Rub, fold, stretch | Material/tension/action rather than a label-only EQ preset |
| Later | Saturated sponge/foam | Squeeze/release | Liquid supply, compression and gas/liquid paths |
| Later | Liquid + container/surface | Drip, pour, splash | Source impacts versus flow and container/air response |

For each entry the JSON records the proposed audible comparison, competing
mechanisms, minimum observations, source links and actual implementation status.
There are 18 entries because several primary actions and object pairs are split.
None is declared to induce ASMR in every listener. “Trigger” here denotes a
candidate sound/action category, not a guaranteed physiological effect.

## Implementation decision

Retain the generic fixture as a numerical reference, not the primary sound target.
The new acoustic source is a deliberately bounded comparison: it exposes event
pooling and bilateral errors rather than establishing physical control. The next
physical implementation needs source discrimination and a fittable transmission
relationship. Collecting a larger unrelated SFX folder, adding guessed bubbles or
replaying convenient library clips does not satisfy that requirement.
