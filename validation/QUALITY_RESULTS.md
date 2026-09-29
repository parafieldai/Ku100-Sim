# Main-renderer quality update: executed evidence

Verified on 29 September 2026. Tested application commit: `40cc3f12dfb41b24cbb9a90ee5268939de132851`.

GitHub Actions [run 36616716883](https://github.com/parafieldai/Ku100-Sim/actions/runs/36616716883) completed successfully using a GitHub-hosted Linux runner. Its `main-quality-preview-36616716883` artifact contains the exact tested source, reports, hosted-site directory, self-contained HTML preview and seven original native stereo WAVs. Artifact SHA-256: `28626669724e46e7bbd4a53e49e795801ea4a15c5e0ae14ca39e4ee3a1f76762`.

## Executed checks

- 69 native/Python tests; 17 frontend tests.
- Original 15-scenario physics probe, plus the new 11-trajectory per-ear/per-band refinement assessment.
- Four-radius analytical circular-tube impedance validation against an independent Bessel-function calculation.
- Nine HTTP browser end-to-end groups, including project-subpath hosting, exact decoded stereo samples, original WAV download hashes, playback, import and scene editing.
- Six offline-browser checks, including all seven examples, original WAV hashes, actual playback, mobile layout and no external requests.
- Browser used by both cloud checks: Chromium 151.0.7922.34. No human listening assessment was performed.

## Results must retain their scope

The positive-memory viscous impedance approximation has a maximum complex relative error of approximately 0.01565% and maximum resistance relative error of approximately 0.3422% over the declared 20 Hz–20 kHz, four-radius grid. This validates that component, not a KU100 contact recording. Thermal admittance is not implemented.

The new unsteady-loss example uses 256 structural modes per plate. The 256/512 comparison meets the declared 0.5% target in sufficiently excited low-frequency bands. High bands with insufficient excitation remain unassessed, never passed. See `quality-assessment.json` in the artifact and [QUALITY_UPDATE.md](../docs/QUALITY_UPDATE.md).

The fine-texture example is an unmeasured microgeometry sensitivity experiment. It is not a calibrated tongue surface or an established improvement in perceived recording realism. Full-band contact fidelity remains unestablished.

## Preview and hosting

Download the Actions artifact and open `outputs/review/Ku100-Research-Preview.html`; no web server is needed. Its `audio` directory contains the original native WAV files. New main CI runs retain the same preview and measurements for 14 days.

At this run, the Pages API returned HTTP 404. No live website is claimed. The publication workflow now accepts public Pages, as authorized, and deploys only a successful main CI run's exact tested `dist` artifact when Pages is configured with GitHub Actions as its source. It does not make the repository or reference recordings public.

The temporary checked, compressed source-transfer files were removed after the tested source commit was published. Subsequent publication changes do not change the physical equations or rendered waveforms.
