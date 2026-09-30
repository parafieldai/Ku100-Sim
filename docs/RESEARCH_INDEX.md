# KU100 research and audit index

Repository of record: `parafieldai/Ku100-Sim`. Main application development is in `native/`, `ku100sim/`, `scripts/` and `web/`. The separately integrated `benchmarks/contact-coupon` is not an interchangeable renderer. Documents and evidence are versioned with the code; historical reports retain their named source versions.

## Start with the requested target

The user rejected the generic plate/chamber sound as unlike the original wet-contact target. [TARGET_REFOCUS.md](TARGET_REFOCUS.md) records the corrected acceptance criteria, four sample-exact reference diagnostics, a separately labeled pressure-release hypothesis, its numerical checks and its failure to explain the complete target. [SFX_TRIGGER_RESEARCH.md](SFX_TRIGGER_RESEARCH.md) separates 12 object/action families and the actual support and access status of the primary sources.

The deployed `target.html` is an audio-first comparison. Public files contain generated audio and derivative measurements only; the reference WAV stays in the visitor's browser. The optional private offline package embeds the user's supplied excerpts and must never be published. No listening judgment is prefilled, and a successful software test does not turn the hypothesis into an accepted wet-ear simulator.

## Current specifications and limits

| Subject | Document | Executable evidence |
|---|---|---|
| Target source hypothesis and local-reference comparison | [TARGET_REFOCUS.md](TARGET_REFOCUS.md) | `tests/test_release_source.py`, `scripts/validate_release.py`, `scripts/browser_target.mjs` |
| SFX objects, actions, materials and transmission | [SFX_TRIGGER_RESEARCH.md](SFX_TRIGGER_RESEARCH.md) | [Research registry](../web/triggers.json), [fixed reference diagnostics](../web/target-reference-summary.json) |
| Coupled contact, Mindlin structure, chambers, duct and radiation | [PHYSICS.md](PHYSICS.md) | `tests/test_physics_audit.py`, `scripts/validate_physics.py` |
| Optional passive unsteady viscous memory | [VISCOUS_LOSSES.md](VISCOUS_LOSSES.md) | `tests/test_viscous.py`, `scripts/validate_viscous.py` |
| Per-ear/per-band refinement, source bandwidth and listening limits | [QUALITY_UPDATE.md](QUALITY_UPDATE.md) | `scripts/quality_gate.py`, `tests/test_quality_gate.py` |
| Device specifications and measurement boundaries | [MICROPHONES.md](MICROPHONES.md) | [Receiver provenance](../data/manifest.json), [orientation](../data/orientation-check.json), [measured-bank validation](../data/validation.json) |
| HF, Kaggle, Figshare and institutional data | [DATASET_RESEARCH.md](DATASET_RESEARCH.md) | [Paired-trial summary](../validation/dataset-paired-trial.json), read-only inspection scripts |
| Uploaded source archives and target-reference limits | [INPUTS_AUDIT.md](INPUTS_AUDIT.md) | Named archive/member hashes in that report |
| Documentation-to-code audit | [IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md) | `tests/test_document_contracts.py`, `web/tests/core.test.js`, [cloud execution receipt](../validation/audits/2026-09-29/CLOUD_RESULTS.md) |
| Separate benchmark integration | [CONTACT_BENCHMARK.md](CONTACT_BENCHMARK.md) | [Benchmark instructions](../benchmarks/contact-coupon/INTEGRATION.md) |

## Historical evidence: keep versions separate

The [delivered main-quality research report](reports/main-quality-update-2026-09-29.md) is checked in. It records the successful `27f6851` CI run, seven original example identities, numerical limits and dataset inspection. It is historical evidence, not the current CI status.

[Durable numerical reports](../validation/reports/2026-09-29-quality/manifest.json) retain the exact historical per-band assessment, analytical impedance validation, paired-trial summary and publication/browser receipts. The compact example summary is a documented derivative of the originally delivered evidence file. Raw performance audio, sensor arrays and downloaded source ZIPs are excluded from Git and the publication site. Generated native listening files are excluded from Git but included in the tested preview/site artifacts.

Earlier implementation-specific audits remain at [physics-audit.md](../validation/physics-audit.md), [receiver-audit.md](../validation/receiver-audit.md), [pipeline-audit.md](../validation/pipeline-audit.md) and [research-audit.md](../validation/research-audit.md). Their old source hashes and test totals must not be presented as fresh reviews of subsequent changes. The [integrated initial validation](../validation/VALIDATION.md) and [quality-update receipt](../validation/QUALITY_RESULTS.md) likewise describe named snapshots.

## Reproduce and retrieve results

Follow the root [README](../README.md). Successful main CI runs retain `dist/`, server-free `outputs/review/target.html`, the original `outputs/review/Ku100-Research-Preview.html`, original stereo WAVs and `validation/local/` reports. Pages deploys only the exact successful main CI artifact. Both the original viewer and target comparison have post-deployment HTTP/browser checks; a successful availability check or skipped deploy is not a live-site pass.

The source papers justify methods and document measurements. Neither cited literature, numerical agreement nor a passing workflow certifies KU100 wet-contact realism. Geometry/material identification, matched bilateral recordings and a human listening assessment remain separate requirements.

## Data-assisted object-impact extension

[Object research and dataset scope](objects/RESEARCH.md) covers three named
RealImpact objects and the new modal/transient source. [Validation boundaries](objects/VALIDATION.md)
and [numerical assessment](../validation/objects/assessment.json) retain the
unmeasured-prior failure and the two distance-transfer failures. These are new
item-specific tapping models, not renamed near-ear textures or new KU100 geometry.
