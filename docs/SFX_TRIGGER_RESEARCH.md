# SFX objects, actions and triggers: evidence inventory

Checked 29 September 2026. The original brief's primary tongue–saliva/artificial-ear target remains first. This update does not replace it with a generic SFX sampler. “Trigger” is a requested object/action/acoustic event, **not a guarantee of ASMR sensation**. Items below are research hypotheses unless explicitly marked implemented.

## Separate four descriptions

1. **Object/material:** tongue, saliva, artificial ear, cotton, bristles, glass, paper, foam, oil.
2. **Action/state:** approach, load, slide, reverse, hold, deform, peel, rupture, release, quiet.
3. **Acoustic observation:** continuous texture, clustered transients, decay, resonances, signed ear level and timing. A descriptive “pop” does not identify a bubble.
4. **Transmission/capture:** internal-mouth airborne source, external airborne source, contact/body transmission, occlusion, capsule and processing.

The checked-in [machine-readable registry](../web/triggers.json) carries 12 entries, their requested action sequence, meaningful physical states, supporting sources and unresolved gaps. These are our research labels, not a claim to reproduce exact UCS category IDs.

| Object/action family | Present status | Why it is distinct |
|---|---|---|
| Tongue–saliva slide/reverse | Target not implemented | Dynamic friction/contact, liquid supply and state history; not stationary Gaussian noise |
| Tongue rolling | Target not implemented | Migrating contact patch, deformation and orientation |
| Tongue peel/release | Target not implemented | Wet adhesion/filament/contact-line hypotheses require discrimination |
| Air-pocket pressure release | Native source probe only | Prescribed pocket expansion/opening; causal air states, not solved tongue or saliva |
| Mouth-internal tongue/palate/lips | Competing hypothesis | Could radiate near the mic without ear contact |
| Cotton swab rub/withdraw | Later, research-only | Distributed fibers and a specific contact path |
| Soft brush/hair strokes | Later, research-only | Bristle/strand dynamics and many moving contacts |
| Nail/tool taps on glass/wood/metal | Later, research-only | Object geometry, supports, impact position and radiation |
| Paper/foil crumpling | Later, research-only | Shell buckling events, not a wet-source filter preset |
| Foam squeeze/burst | Later, research-only | Actual films and entrainment; soap/water results do not identify saliva events |
| Oil massage | Later, research-only | Different rheology/wetting/contact pair, not renamed “wetness” |
| Stress-ball compress/release | Confound/control | Some historical target intervals mix opposite-ear actions |

## Primary sources and actual access status

### Oral contact and competing mouth sources

**Acoustic emission measurement of rubbing and tapping contacts of skin and tongue surfaces in relation to tactile perception** (2013), Food Hydrocolloids, [DOI 10.1016/j.foodhyd.2012.11.020](https://doi.org/10.1016/j.foodhyd.2012.11.020). Publisher abstract inspected. Reports contact acoustic measurements involving skin and tongue/palate/food in a limited participant apparatus. **No raw trial acquired; not tongue/artificial-ear calibration.** It supports treating oral rubbing/tapping as a distinct measurement problem, not assuming all mouth transients are pressure releases.

**Negative intraoral pressure in German: Evidence from an exploratory study** (2013), Journal of the International Phonetic Association, [DOI 10.1017/S0025100313000236](https://doi.org/10.1017/S0025100313000236). Publisher abstract inspected. Negative oral pressures and some clicks are observed in speech-pause contexts; clicks need not establish a simple double closure. **Not ASMR, not a fitted pressure/opening trajectory.** The new source is a falsifiable competing hypothesis, not a reproduction of this experiment.

### Saliva and liquid-interface sound

Wagner & McKinley, **Age-dependent capillary thinning dynamics of physically-associated salivary mucin networks** (2017), [MIT author bibliography](https://nnf.mit.edu/biblio/article-271/). Indexed author abstract inspected; a subsequent direct-page request returned 502. It distinguishes evolving filament/relaxation behavior from relatively unchanged shear rheology during aging. **No ear/audio data acquired.** A single viscosity scalar cannot represent all saliva history or thread behavior.

Bussonnière, Antkowiak, Ollivier, Baudoin & Wunenburger, **Acoustic sensing of forces driving fast capillary flows** (2020), Physical Review Letters 124, 084502, [DOI 10.1103/PhysRevLett.124.084502](https://doi.org/10.1103/PhysRevLett.124.084502). Primary abstract inspected. Microphone-array measurements of bursting soap films connect sound to capillary forces in that apparatus. **Not proof that the target contains bubble collapse; no audio imported.** Film force radiation is a competing source class and should not be silently replaced by a generic Helmholtz pop.

Langlois, Zheng & James, **Toward Animating Water with Complex Acoustic Bubbles** (2016), [author project](https://www.cs.cornell.edu/projects/Sound/bubbles/). Author abstract and available code/audio links inspected, not downloaded or executed. Geometry, topological events, bubble boundaries and cavity effects matter. The authors validate a frequency model with physical experiments. **Water/two-phase results do not validate saliva between soft surfaces.** The site retains copyright restrictions; linked WAVs are not assumed redistributable.

Bilbao & Harrison, **Passive time-domain numerical models of viscothermal wave propagation in acoustic tubes of variable cross section** (2016), [primary bibliographic record](https://pubmed.ncbi.nlm.nih.gov/27475194/). Source for the existing passive tube work. New release source reuses the repository's independently checked **viscous-only** component. Thermal effects and moving-neck reactive effects are not claimed.

### Object events, useful taxonomies and dataset boundaries

Cirio, Li, Grinspun, Otaduy & Zheng, **Crumpling Sound Synthesis** (2016), [author project](https://www.cs.columbia.edu/cg/crumpling/). Author project/abstract inspected. It links buckling events and evolving shell geometry to modal sound, including a perceptual study. **No code, model or WAV acquired in this update.** This is a much more specific paper/foil route than reusing a wet-source generator.

Huh et al., **EPIC-Sounds: A Large-scale Dataset of Actions that Sound** (2023), [author project](https://epic-kitchens.github.io/epic-sounds/) and [paper](https://arxiv.org/abs/2302.00646). Event annotations and material/visual grounding help organize object/action observations. **No trial fetched or calibrated contact-force mapping inferred here.** Project releases/abstract totals differ; this inventory does not silently merge their counts.

Yang, Russell & Salamon, **Telling Left from Right: Learning Spatial Correspondence of Sight and Sound** (CVPR 2020), [author project](https://karreny.github.io/telling-left-from-right/), [YouTube-ASMR-300K release](https://zenodo.org/records/3889168). Metadata inspected. The release contains **URL lists**, not a ready-to-download rights-cleared 900-hour WAV collection. Useful for spatial/action research, not exact KU100 identification. No video downloaded or audio used at runtime.

Fonseca et al., **FSD50K**, [official release](https://fsannotator.upf.edu/fsd/release/FSD50K/), [paper](https://arxiv.org/abs/2010.00475). Official event-label and licensing metadata inspected. Useful reference/labeling resource, not paired tongue/contact mechanics. Rights belong at the clip level; no clips downloaded or redistributed here.

**Universal Category System**, [official project](https://universalcategorysystem.com/). Public-domain categorization/filename initiative inspected. Useful organizational vocabulary, **not physical evidence**. This registry is an authored object/action/state map, not a claim of conformance to an uninspected category spreadsheet.

The earlier [HF/Kaggle/Cluster audit](DATASET_RESEARCH.md) and [paired-trial summary](../validation/dataset-paired-trial.json) remain valid scoped evidence. This update does not claim fresh HF/Kaggle audio ingestion. The inspected HF source that removes saliva sounds is specifically unsuitable for the primary target. A general SFX corpus is not a substitute for the missing joint source/action/transfer evidence.

## Most informative next evidence, not the largest corpus

The current four-second target cuts show sustained activity and multiple envelope events absent from the sparse pressure-release probe. Preserve the negative comparison. Distinguish *same mouth action away from the ear* versus *ear-contact*, then dry/wet contact and controlled separation. This tests source location and interaction dependence rather than accepting a mechanism because its equation is familiar. Video/force synchronization, provenance and raw microphone processing must be explicit. Detailed measurement of every microscopic state is not a prerequisite; the smallest observations that discriminate source hypotheses are the goal.

All source statements above are distinct from the supplied handoff requirements, our proposed experimental controls, measured file descriptors and the new code's numerical checks. None certifies the new sound as realistic or records a human listening result.
