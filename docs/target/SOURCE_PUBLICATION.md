# Source-texture iteration: executed validation and publication

30 September 2026 UTC / 29 September Los Angeles time.

The user reports that the earlier sources feel near the ear and suggest ear picking but have the wrong ASMR SFX character. This change investigates the source waveform, not a new spatial effect or a claimed ASMR response. See [SOURCE_ITERATION.md](SOURCE_ITERATION.md) for fitting populations, primary research, methods, development results and limits.

## Executed source-validation run

[GitHub Actions run 36663812949](https://github.com/parafieldai/Ku100-Sim/actions/runs/36663812949) succeeded. Expanded tested source commit: `00101cdc3ea34049d25fc0d28686abf07c68020c`, based on main `def7f4bed82393f23192fcd14dd1cc279ed6fd29`. The final integration removes only the temporary source-transfer workflow and adds the same source checks to regular main CI and post-deployment verification.

The cloud run passed 115 native/Python tests, 25 frontend tests, existing numerical/native and target-source checks, original viewer HTTP/offline tests, both existing target comparisons, and the new source-browser checks. All seven new comparison WAVs were generated in the runner without reading the user's recordings.

The new Chromium 151.0.7922.34 source-page run passed six groups: all 13 served assets matched the built files; revised source selected by a stable name without reference loading; seven WAVs decoded sample-exactly, played, stopped and downloaded unchanged; source-only mode duplicated the actual near channel without changing the original stereo download; a synthetic local reference exercised crop/hash handling and invalid-input refusal without uploading; desktop/mobile layouts fit. The synthetic import fixture is not the user's reference recording and not a listening judgment.

The downloaded artifact `source-texture-review-36663812949`, ID `11075611462`, is 68,945,302 bytes with SHA-256:

```
288b63da4c3a2898bffc39a02080b046f3cf210cf7777e0f3d624327775dc753
```

Every ZIP CRC passed. All 19 expanded source/document files and the three compact parameter models in its source archive were checked byte-for-byte against the locally tested files. The transport parts are absent from the expanded source. Local combined verification also passed all 115 Python/native tests and 25 frontend tests. Actual browser execution occurred in GitHub Actions, not the browser-less local container. No LLM subagents or human listener assessment are claimed.

## Listen and interpret

The publication target is [Source sound — Revision 2](https://parafieldai.github.io/Ku100-Sim/source/). The page offers revised right and left sources, a separately range-fitted right source, previous burst sources, and same-spectrum phase controls. Generated audio is playable without loading any recording. Original reference import is optional and stays browser-local. The older `/target/` page now uses stable names by default; blind randomization is opt-in.

Two revised examples use statistics fitted to the displayed reference excerpts. They are same-excerpt representation experiments, **not held-out prediction or validated physical synthesis**. The range-fitted right model excludes the displayed reference segment, which was nevertheless previously inspected. All panel sources share one frozen inter-ear filter per side; that is a comparison control, not newly calibrated ear geometry. The phase controls preserve generated Fourier magnitudes before the declared boundary fade, not every subsequent windowed spectral estimate.

Current metrics and model hashes are retained in each successful main CI artifact under `validation/local/source-iteration.json` and `dist/source/generated/iteration.json`. Neither objective reduction, spectrum agreement, playback tests nor a successful deployment establishes the requested ASMR sound. The native C++ models remain unchanged, the new path is explicitly microphone-domain statistical synthesis, and target acceptance stays false until supported by the required evidence.

Main CI, actual Pages deployment, and public-HTTPS browser verification must be checked separately at the final integration commit. This prepublication receipt alone is not a deployment claim. No raw target waveform, private comparison page, or original recording is published.
