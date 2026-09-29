# KU100 research and audit index

Repository of record: `parafieldai/Ku100-Sim`. Main application development is in `native/`, `ku100sim/`, `scripts/` and `web/`. The separately integrated `benchmarks/contact-coupon` is not an interchangeable renderer. Documents and evidence are versioned with the code; historical reports retain their named source versions.

## Current specifications and limits

| Subject | Document | Executable evidence |
|---|---|---|
| Coupled contact, Mindlin structure, chambers, duct and radiation | [PHYSICS.md](PHYSICS.md) | `tests/test_physics_audit.py`, `scripts/validate_physics.py` |
| Optional passive unsteady viscous memory | [VISCOUS_LOSSES.md](VISCOUS_LOSSES.md) | `tests/test_viscous.py`, `scripts/validate_viscous.py` |
| Per-ear/per-band refinement, source bandwidth and listening limits | [QUALITY_UPDATE.md](QUALITY_UPDATE.md) | `scripts/quality_gate.py`, `tests/test_quality_gate.py` |
| Device specifications and measurement boundaries | [MICROPHONES.md](MICROPHONES.md) | [Receiver provenance](../data/manifest.json), [orientation](../data/orientation-check.json), [measured-bank validation](../data/validation.json) |
| HF, Kaggle, Figshare and institutional data | [DATASET_RESEARCH.md](DATASET_RESEARCH.md) | [Paired-trial summary](../validation/dataset-paired-trial.json), read-only inspection scripts |
| Uploaded source archives and target-reference limits | [INPUTS_AUDIT.md](INPUTS_AUDIT.md) | Named archive/member hashes in that report |
| Current documentation-to-code audit | [IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md) | `tests/test_document_contracts.py`, `web/tests/core.test.js`, [cloud execution receipt](../validation/audits/2026-09-29/CLOUD_RESULTS.md) |
| Separate benchmark integration | [CONTACT_BENCHMARK.md](CONTACT_BENCHMARK.md) | [Benchmark instructions](../benchmarks/contact-coupon/INTEGRATION.md) |

## Historical evidence: keep versions separate

The [delivered main-quality research report](reports/main-quality-update-2026-09-29.md) is now checked in. It records the successful `27f6851` CI run, seven original example identities, numerical limits and dataset inspection. It is historical evidence, not the current CI status.

[Durable numerical reports](../validation/reports/2026-09-29-quality/manifest.json) retain the exact historical per-band assessment, analytical impedance validation, paired-trial summary and publication/browser receipts. The compact example summary is a documented derivative of the originally delivered evidence file. Raw performance audio, sensor arrays and downloaded source ZIPs are excluded from Git and the publication site. Generated native listening files are excluded from Git but included in the tested preview/site artifacts.

Earlier implementation-specific audits remain at [physics-audit.md](../validation/physics-audit.md), [receiver-audit.md](../validation/receiver-audit.md), [pipeline-audit.md](../validation/pipeline-audit.md) and [research-audit.md](../validation/research-audit.md). Their old source hashes and test totals must not be presented as fresh reviews of subsequent changes. The [integrated initial validation](../validation/VALIDATION.md) and [quality-update receipt](../validation/QUALITY_RESULTS.md) likewise describe named snapshots.

## Reproduce and retrieve results

Follow the root [README](../README.md). Successful main CI runs retain `dist/`, the server-free `outputs/review/Ku100-Research-Preview.html`, original stereo WAVs and `validation/local/` reports. Pages deploys only the exact successful main CI artifact when Pages is configured; a successful availability check or skipped deploy is not a live site.

The source papers justify methods and document measurements. Neither cited literature, numerical agreement nor a passing workflow certifies KU100 wet-contact realism. Geometry/material identification, matched bilateral recordings and a human listening assessment remain separate requirements.
