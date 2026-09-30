# Final main and live verification — 30 September 2026

## Tested and deployed code

Application commit: `f20ab7dffa1c5990ec265e96c93bbe2d2c90628e`.

- [Main CI 36752742618](https://github.com/parafieldai/Ku100-Sim/actions/runs/36752742618): all build, regression, numerical, generation and browser steps succeeded.
- [Pages publication 36754494993](https://github.com/parafieldai/Ku100-Sim/actions/runs/36754494993): both prepare and actual deploy jobs succeeded.
- [Public-site verification 36754605646](https://github.com/parafieldai/Ku100-Sim/actions/runs/36754605646): all legacy and new shared-engine checks succeeded.

The live site is `https://parafieldai.github.io/Ku100-Sim/unified/`.
Chromium 151.0.7922.34 checked all 25 shared-page assets against the exact main
artifact, and all seven 48 kHz stereo WAVs had zero decoded-sample discrepancy.
Playback, completed seeking, original downloads, edited-scene JSON and the rule
that editing does not alter precomputed playback were tested. Desktop and mobile
layouts passed without application errors. The physical source is the same one
kernel as in [CLOUD_RESULTS.md](CLOUD_RESULTS.md), not seven object-specific solvers.

## Downloaded artifact integrity

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Main artifact 11116665380 | 101184026 | `aeeff10045e6e14b6bae1fff072c34b2950070d0a738b90daa596c550ee27782` |
| Live artifact 11115878353 | 5753344 | `84013826bc79be84d8c9b9eb7bdf00f09b514dce5e42bc01f1beeb024e77835d` |

Both artifacts were downloaded and their full hashes and ZIP CRCs verified.
Every generated shared scene, state trace and WAV matches its manifest. All seven
new WAVs are also byte-identical to the pre-integration branch validation output.
The 28 new local tests were rerun successfully after main integration.

The executable main code, scenes and workflow have not changed in the subsequent
document-only receipt commit. That commit uses `[skip ci]` to avoid regenerating
the same large example suite for a provenance correction; it is not claimed to
have another new green run or deployment. The named application commit above is
the one actually tested and deployed.

## Important correction: legacy algorithms versus waveform preservation

An earlier pre-integration statement that all existing generated audio would
remain unchanged was too strong. The old source algorithms, fitted parameters
and native mechanical definitions were not changed, but the full main pipeline
regenerates the previews rather than freezing their previous published bytes.

Compared against the previous `c4ef705` main artifact:

- 18 of 33 older audio payloads are byte-identical.
- Six older burst/control payloads have differences no larger than
  `2.3e-16` in normalized samples; no perceptual equivalence claim was tested.
- Nine optimizer-derived or derived-control payloads differ more substantially.
  The seven revised/long texture payloads have waveform difference SNRs of about
  3.20 to 6.88 dB; two phase controls have 8.28 and 9.92 dB. These are cross-run
  numerical comparisons, not quality ratings. The cause of the cross-run
  optimizer variation was not isolated in this implementation task.

Therefore the legacy *methods and model definitions* are preserved, not all exact
prior waveforms. Prior listening verdicts belong to their prior artifact hashes.
The saved previous main artifact is `11105388890` from run `36731857656`, SHA-256
`ed6ef9788e56582fbf043dd3f17bad3431908bbd43fdc48046d5b37092820cdf`.
Stable versioned audition assets and stricter optimizer reproducibility are
separate follow-up work; a fixed seed alone must not be advertised as an exact
cross-run waveform guarantee. None of these older texture generators is used to
synthesize the new shared-engine demonstrations.

## Scientific scope remains bounded

The seven examples are unmeasured reduced-coordinate mechanical prototypes.
The preview signal is weighted velocity, not calibrated microphone pressure.
There is no full shell mesh, identified soft-silicone material, tangential
friction/fluid/seal model, fork-directional radiation or new KU100 capture model.
No source recording or fitted acoustic texture was used for these seven examples.
No human listening assessment or new LLM-subagent audit was performed. Numerical
and browser success does not establish realistic ASMR or material identity.
