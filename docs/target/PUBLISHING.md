# Publishing the saved six-candidate listening comparison

This integration adds the previously delivered `02ed375` acoustic study at `target/` without replacing the newer native pressure-release study at `target.html`, the seven-example fixture viewer, or any native physical equations.

Open `https://parafieldai.github.io/Ku100-Sim/target/`. Generated audio works without loading a reference: select a candidate and press **Play candidate from start**. Reveal the identity to see its exact method and measurements. Choose a left-ear reference descriptor to expose left-profile candidates. The six files comprise three freshly generated empirical burst takes, one continuous negative control, and two preserved native-fixture baselines.

Raw user reference WAVs and the private comparison HTML are not published. Optional reference comparison reads the original files locally in the visitor's browser; original gain and channel relationships are retained. A hosted public reference upload was not authorized by this integration.

`docs/target/DELIVERY.md` and `LOCAL_RESULTS.md` describe the earlier unpushed snapshot. They are retained as history, not current deployment receipts. The source-model limitations and negative acoustic findings remain unchanged. Publication is not an acceptance or realism claim.

CI regenerates the six files from the checked-in aggregate model parameters and declared native scenes, checks the privacy allowlist, tests playback/import/downloads, and includes them in the existing exact-artifact Pages pipeline. The post-deployment check separately verifies `/target/`, every generated WAV's hash, playback and mobile layout. The other agent's `/target.html` study and its checks are preserved.
