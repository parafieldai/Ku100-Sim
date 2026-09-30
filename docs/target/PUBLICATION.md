# Saved listening comparison publication

The saved six-candidate empirical comparison has been integrated on top of main source `8d300935f43ce660e25a35cbaa4e77f82e8920af`, preserving the newer native pressure-release study, the main renderer and all existing scene definitions. The integration adds `/target/`; it does not replace `/target.html`.

## Executed prepublication validation

[GitHub Actions run 36654951335](https://github.com/parafieldai/Ku100-Sim/actions/runs/36654951335) completed successfully. Its expanded, tested source commit is `46c4577564615a85bb549f7021d022fcaa81bcb6`. The run verified the exact integration patch, built the native renderer, prepared the measured bank, ran the complete Python and frontend suites, checked physical refinement and release-source diagnostics, generated the existing and added examples, and exercised playback/downloads for the main viewer and both comparison pages. The additional saved-comparison import test uses a synthetic stereo fixture, not a public copy of user reference recordings.

Integration patch SHA-256: `055efd2627cf7f77c811187ba0b77e9a0731aaaf851b6ed56e5a6499408e2fa3`.

The temporary transport files were removed from the expanded source. The temporary publication workflow is removed by this final connector-authored commit; regular main CI and post-deployment verification now include the new page. Main CI, actual Pages deployment and live browser verification are separate runs and must each be checked at their actual commit before claiming a live publication.

## Listening

Open [the saved listening comparison](https://parafieldai.github.io/Ku100-Sim/target/), select a candidate and press **Play candidate from start**. Generated audio works immediately without loading a reference file. Choose **Reveal method & measurements** to inspect the method identity and limitations. Selecting a left-ear reference descriptor exposes the left-profile candidates.

The public page has six generated files: three empirical burst takes, one continuous negative control and two native-fixture baselines. Neither the empirical model nor the pressure-release hypothesis is an accepted realistic wet-ear simulator. Playback verification is not a human listening judgment.

Original reference WAVs and `Ku100-Target-Comparison-PRIVATE.html` are not included in Git or the public site. Reference comparison is optional and reads the original files locally in the listener's browser. Historical delivery/local-test documents remain tied to the earlier unpushed snapshot; this receipt records the later publication integration.
