# Document-to-implementation audit — 29 September 2026

## Scope and review identity

This review reconciles KU100-Sim branch history and checks the main application against the repository specifications, the supplied KU100 handoff, and the delivered quality-update report. It excludes the unrelated Parafield/Manish/V2 discussion in the same pasted handoff. Source snapshot: `7d3b7fe5762de10ebd63afe76cb14978e774032f`, whose application parent is `27f685172a19ab5cd8829da93195e91a01f6b09b`.

**Review execution:** one assistant's source/document review plus separately implemented automated mathematical, native, pipeline and browser checks. No new LLM subagents could be invoked in this session. Parallel test processes are not described as subagents. Historical documents reporting earlier subagent activity are preserved as historical claims, not adopted as the authorship of this audit.

## Branch reconciliation

At inspection, `native-physics-audit` (`318602a`) was an ancestor of main with zero unmerged commits (16 commits behind application head `27f6851`). `research-audio-quality` (`b83ae11`) was also an ancestor with zero unmerged commits (one behind). No conflict resolution, duplicate merge, branch deletion or forced ref replacement was needed. The old branch's benchmark remains under `benchmarks/contact-coupon`; main's application paths are preserved. New audit fixes, documentation and evidence are added on top of this history.

## Document-to-code traceability

| Documented contract | Implementation checked | Verification and remaining boundary |
|---|---|---|
| New physical waveforms; no recorded performance excitation | `native/physics.cpp` driver and contact path; `native/main.cpp` input options | Source inspection and native pipeline tests. Measured HRIR is receiver data, not an ASMR performance source. |
| Mass-normalized Mindlin modes and adjoint contact/pressure ports | `mindlin_block`, `make_modes`, `simulate` | `test_physics_audit.py` independently assembles modal energy and coupled midpoint equations. This is a generic plate, not a measured KU100 pinna. |
| Discrete contact potential and nonnegative loss | `spring_gradient`, `contact_solve` | Quadrature/root references and loss tests. Smooth friction is not adhesive rupture or true sticking. |
| Optional unsteady viscous tube losses load the source | `native/viscous.hpp`, tube/vent Schur terms and energy accumulation in `simulate` | Bessel reference, positive coefficients, driven/undriven work checks, four-radius validation. Thermal losses remain absent. |
| Measured receiver orientation, single distance correction, full filter tails | `native/receiver.cpp`, `scripts/prepare_ku100.py`, manifest | Independent DSP tests and bank identity checks; near-field airborne data does not establish wet-contact transmission. |
| One declared common gain; raw Pa exports retained | `native/main.cpp`, `scripts/render.py` | Pipeline gain/over-full-scale/identity checks. No limiter or arbitrary opposite-ear gain was added. |
| Reproducible native producer and original audio identity | Build receipt, binary/source hashes, scene digest, WAV SHA-256 | Native pipeline and browser integrity tests. Historical build hashes remain version-specific. |
| Per-ear/per-band qualification with weak-band refusal | `scripts/quality_gate.py` | Fixed window, no gain/delay fitting, explicit weak-excitation state; required preview comparisons are 20–500 Hz only. |
| Exported scenes must be renderable by the supported decimator | Python scene contract, browser validation, native decimator | A 1,536/768 kHz contract mismatch was fixed at the scene/viewer boundary; pure-core probe capacity is unchanged. |
| Invalid imports fail cleanly; partial geometry uses native defaults | RIFF reader, numeric publication predicate, scene editor | Four input-contract defects below have regression coverage. No audio equations were retuned. |
| Publication is allowlisted and uses tested main artifacts | `scripts/build_site.py`, `package_preview.py`, Pages workflow | Existing path/symlink/hash tests plus malformed-number regression. Public Pages authorization does not expose user recordings or change repository visibility. |
| Calibration and human listening remain unestablished | Provenance flags, docs and output labels | Kept explicitly false/not performed; this audit supplies no invented listening results. |

## Findings and fixes

### A1 — Zero-bit WAV header could cause division by zero

`read_wav` checked `len(payload) % align` before rejecting unsupported bit depths. A valid-sized RIFF container with PCM depth 0, alignment 0 and byte rate 0 raised `ZeroDivisionError`, rather than its invalid-input `ValueError` contract. The reader now validates encoding/bit depth before arithmetic and explicitly rejects nonpositive frame alignment. Supported PCM16/24/32 and Float32/64 sample values and ear order remain unchanged.

### A2 — Huge JSON integers leaked an overflow from the publication predicate

`_number(10**400)` raised `OverflowError`. The site CLI already caught that exception, but the reusable validator did not consistently reject it through its ordinary `ValueError` contract. `_number` now returns false for overflowing integers. A malformed bundle-duration regression verifies normal rejection. This is input handling, not a demonstrated remote exploit.

### A3 — Partial geometry could bypass browser checks

The scene editor checked plate aspect ratio and contact-footprint size only when both dimensions were explicitly supplied. It accepted `{contact_radius_m: 0.04}` with omitted default dimensions, and `{plate_width_m: 0.9}` with omitted height; native validation rejects these. Browser checks now resolve omitted width, height and footprint from the existing native defaults before coupled validation. Tests cover both rejected and valid sparse overrides.

### A4 — Viewer advertised integration rates the export path cannot use

The physics-only API supports up to 1,536 kHz, but the native output decimator permits integer multiples of 48 kHz only up to 768 kHz. The browser previously accepted 1,536 kHz. Python scene validation and the viewer now enforce the export limit. The physics API is not reduced, and no timestep, threshold or waveform is changed for existing scenes.

### A5 — Documentation lagged the implementation

The main physics page described only quasi-steady wall resistance and omitted the new memory-state energy/loss terms. It now distinguishes legacy and unsteady options and links their equations. The README's old private-only/manual Pages description did not match the public-capable tested-artifact workflow. It now documents the actual artifact and Pages behavior. This does not claim Pages has deployed.

## Executed local evidence

The restored snapshot passed 69 native/Python tests and 17 frontend tests. After the fixes, 75 native/Python tests and 19 frontend tests passed. Six new Python test methods and two frontend test groups cover the input-contract defects. The original fifteen-scenario physics probe, eleven-trajectory quality assessment and four-radius analytical viscous validation were rerun successfully. Numerical guards were not relaxed.

The local environment used Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0 and h5py 3.15.1 with the installed C++ compiler. GitHub CI separately uses its declared Python 3.12 environment. Local pass claims do not stand in for unobserved cloud runs; retrieve the final commit's CI artifact for its actual logs, browser version and generated preview.

The native C++ source and all seven shipped scene JSON files are unchanged by these audit fixes. Thus the fixed input-validation paths do not constitute a new sound-generation model or an asserted audible improvement. Both successful and failed historical numerical experiments are retained.

## Unresolved scientific requirements

The generic fixture has no measured target-device pinna/internal geometry, identified viscoelastic material law, wet-adhesion/free-surface/bubble model or calibrated contact-to-capsule transfer. A 20–500 Hz regression qualification is not 20 kHz structural convergence. Reference recordings still lack matched force, motion and device provenance. The present acoustic loss model is viscous, not complete viscothermal acoustics. There is no human listening validation. These are documented research gaps, not issues fixed by branch merging or UI validation.

## Reproduction

Run the root README commands. Additional targeted checks:

```sh
python -m unittest discover -s tests -p test_document_contracts.py -v
npm --prefix web test
python scripts/validate_viscous.py
python scripts/quality_gate.py
python scripts/check_research_index.py
```

The [research index](RESEARCH_INDEX.md) links current specifications and historical evidence. Durable reports under `validation/reports/2026-09-29-quality/` retain exact original receipts and a file-hash manifest; generated WAVs and full raw trials remain artifact-only.
