# Coupled-body development verification — 30 September 2026

The [development validation run 36778363559](https://github.com/parafieldai/Ku100-Sim/actions/runs/36778363559) executed the expanded source patch on baseline `56275aa5fc39a0ae1defa26fb4c263f64147926d`. Its exact tested source tree is `9aacd4378d3ad69dd1384127ef0ac6ecd47e9b26`.

All **61 selected tests passed** in 5.569 s: 15 new interaction tests, 20 existing shared-engine tests, 18 binaural receiver tests and eight publication tests. This is not the whole repository suite. Both prior local full-suite attempts timed out during legacy pipelines; they are not represented as successful runs.

The three-second opposed grip was independently rerendered at 192 and 384 kHz. Relative velocity discrepancy is `7.0225756940463755e-6`, below the unchanged 0.005 limit. Endpoint loads on the two finger contacts and internal solid link approach 2.0210 N during the measured hold; quartering one contact's stiffness changes that to about 1.7750 N. Both contacts detach after release. The parameters and forces are unmeasured reduced-model predictions, not human-hand data.

The artifact `body-interactions-36778363559`, ID `11126986172`, is 626688 bytes with SHA-256 `3ec00a6b7f3de8c2dfb526dcca04a87fca634e20b4d3de4ecdd53412584ee57a`. It was downloaded and all ZIP CRCs passed. All seven changed executable/scene files match the locally tested byte counts, SHA-256 hashes and Git blob IDs. The GitHub connector assembled the exact tested tree from those blobs. The research documents, this receipt and ongoing lightweight workflow are additional files; they do not modify the tested equations. Temporary binary transport parts and apply workflow are absent from the published branch tree.

The artifact includes full test output, `check/report.json`, `check/grip-trace.csv`, source hashes, source archive and tested tree identity. Reports and original local results remain independently available in the conversation's delivery package.

The ordinary render/export contract remains binaural. The test suite exercised that path without using a source recording, but there is **no new public listening example or Pages deployment**. No 3D articulated hand, frictional/tangential contact, fluid simulation, material-specific fit, external-solver execution or human listening pass is claimed.

Native source SHA-256: `a3a795fec5b12dc1fe8b7bbd05463f0bf8cf0e8b4b7aac0954a0108cd7bdbae3`.
Python API SHA-256: `58b91fdd3a618cf6f917098ba89102990c55fdb97649a98fff72515d0c0a45db`.

See [HAND_OBJECT_WATER.md](../../docs/engine-rebuild/HAND_OBJECT_WATER.md) for the old source diagnosis and the remaining multi-body/fluid/acoustic requirements. This work is kept on `body-pair-interactions` so a component test is not silently advertised as improved ASMR audio on main.
