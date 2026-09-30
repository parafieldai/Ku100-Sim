# Object-SFX continuation and reproducibility check — 30 September 2026

## Recovered work, not a restarted or silently substituted experiment

The interrupted `sfx-object-validation` branch already contained the wood-plate,
ceramic-mug and glass-goblet experiment. Its [last validation run](https://github.com/parafieldai/Ku100-Sim/actions/runs/36682536052)
passed all 145 native/Python tests, frontend checks, object generation and the
nine-audio browser test. The run as a whole FAILED while saving expanded Git
objects, after those checks; that is not reported as an entirely green workflow.

The complete artifact `11082422471` was downloaded and verified: SHA-256
`54381b6312fb8758397cb40e5d9310d211c7256b9475e4d76e5ba525f3017bcc`, all ZIP CRCs valid.
Its source tree is exactly `1243df1c22beef6df12b8677d9c9191961f79d63`.
A separate [recovery job](https://github.com/parafieldai/Ku100-Sim/actions/runs/36730989097)
stored the 25 tested changed files as Git blobs without updating any branch.
Every returned Git blob ID, byte count and SHA-256 matched the recovered source.
The authorized GitHub connector assembled the exact tested tree. Temporary
transport parts and apply/recovery workflows are absent from that tree. The
original data-acquisition workflow and reproducible scripts remain.

## Fresh checks in this continuation

The 15 object-model/publication tests were rerun successfully. These include an
independent matrix-exponential oscillator reference and explicit no-file-read
synthesis. The original native mechanical solver was not modified.

The [RealImpact subset acquisition](https://github.com/parafieldai/Ku100-Sim/actions/runs/36677538901)
artifact `11080433670` was also downloaded afresh. Its SHA-256 is
`84bd0ffeb177c3435092076ec2971d11efddc2632fded7d053c3610d8758daaf`; all artifact ZIP
CRCs passed. The three local array hashes match those recorded in the fitted
profiles. The source arrays have four rows each: 208691 samples per wood row,
231321 per ceramic row, and 208457 per glass row, at the paper's 48 kHz rate.
They are the authors' force-corrected MONO measurements, not raw binaural ASMR.

Re-evaluation with the frozen profiles and original three diagnostic seeds
reproduced all reported selected-model spectral/decay numbers to maximum absolute
numerical difference below `3e-15`. No model, criterion, split or source interval
was changed. Rows 22/37/52 remain development position tests that were previously
inspected, not newly blind holdouts. They must not be described as unseen-object
or calibrated microphone validation.

| Object | Unmeasured prior, fitting-position spectral RMSE | Measured profile, same position | Other-position diagnostic passes |
|---|---:|---:|---:|
| Wood plate | 26.0702 dB | 2.8168 dB | 3/3 |
| Ceramic mug | 31.0284 dB | 3.2342 dB | 2/3 |
| Glass goblet | 33.2939 dB | 2.2647 dB | 2/3 |

The farther ceramic/glass spectral failures (8.4061/12.2867 dB) remain failures.
Normalized spectral and energy-decay screens are not measured realism ratings.
See [RESEARCH.md](RESEARCH.md), [assessment.json](../../validation/objects/assessment.json),
and [the initial modal-only attempt](../../validation/objects/initial-modal-only.json).

All nine example WAVs were generated again with Python audio/NumPy-file read
attempts rejected during generation. There were zero such attempts, and the nine
WAV SHA-256 values matched the previous cloud artifact byte for byte. The models
contain modal residues (including parametric phase) and, where selected, small
band-variance tables. No recording buffer or recorded residual is a runtime
asset. These checks establish reproducible parameter-driven generation, not a
universal anti-memorization proof.

## What is and is not being delivered

Three distinct object/material profiles with one action family: tapping.
Each has shorter and longer contact-pulse examples plus an unmeasured diagnostic
prior. The two pulse variants share the same event times and per-object gain;
they are not pitch-shifted versions of the ear texture. Output is deliberately
dual mono to judge the source sound without a binaural illusion. No KU100/3Dio
transfer or physical pressure calibration is asserted for this panel.

This continuation does not deliver validated brushing, crumpling, liquid or
wet-ear source mechanisms. Research on those families remains separate. The
original ear-texture and longer-audio pages stay available and unchanged in their
generated waveforms. No user-supplied ear recordings were used for these object
profiles or published. No new LLM subagent or human listening test was performed.

The final main CI, actual Pages deployment and live HTTPS playback must be
checked at their actual post-integration commit. A green artifact-recovery run
is not a deployment or an acoustic-quality pass.
