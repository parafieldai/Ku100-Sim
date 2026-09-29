# Executed cloud document audit — 29 September 2026

## Tested source and publication distinction

Exact tested source commit: `f578d1ff8c247e745d59261834702bd28579bcae`.

[Audit run 36625852793](https://github.com/parafieldai/Ku100-Sim/actions/runs/36625852793) completed all source, native, benchmark and browser verification steps successfully. **The workflow as a whole ended in failure at its final Git push:** its Actions token lacked permission to update `.github/workflows/ci.yml`. The validated commit was subsequently published through the existing authorized GitHub connector, without a force push. A failed publication step is not described as a fully green audit workflow.

The preceding run [36625296001](https://github.com/parafieldai/Ku100-Sim/actions/runs/36625296001) passed main/document checks but stopped before benchmark tests because the temporary combined workflow omitted the benchmark's separate `soundfile` dependency. The complete benchmark requirements were installed for the rerun. No test assertion, physical threshold, native equation or source scene was weakened to pass either run.

## Executed verification

| Suite | Observed result |
|---|---|
| Main native/Python tests | 75 passed; zero failures or skips |
| Frontend contract tests | 19 passed; zero failures or skips |
| Original physical refinement probe | 15 scenarios passed their declared checks |
| Per-ear/per-band quality assessment | 11 trajectories; required qualified-band guards passed; full-band fidelity remains false |
| Analytical viscous validation | Four radii, independent Bessel-function reference; passed |
| Isolated contact-coupon benchmark | 67 acceptance checks passed; its own refinement limits remain recorded |
| Benchmark measured convolution | Both channel implementation comparisons passed |
| Benchmark ideal sphere | Series and static-limit checks passed; not KU100 fidelity |
| Repository document/evidence integrity | 44 relative links and six archived report hashes passed at the tested source |
| Main HTTP browser run | Nine end-to-end groups passed |
| Main offline preview | Six checks passed, including all seven original WAV identities and actual playback |

Cloud environment: Ubuntu 24.04.5, Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1, GNU C++ 13.3.0, Node 22.23.2 and Chromium 151.0.7922.34. Benchmark dependency resolution installed soundfile 0.14.0 and Python Playwright 1.63.0; the main browser checks use the repository's separate locked Node dependency.

## Retained artifact and independent byte verification

Artifact: `ku100-document-audit-36625852793`, ID `11060067124`, 29,384,272 bytes. SHA-256:

```text
9411f0fbc78743e1b814c7a896bccb95c1d4de235187207612e42d56a1425c9d
```

The artifact was downloaded and every ZIP CRC verified. All **21 changed source/document/evidence files** in its embedded source archive match the expected locally audited byte counts and SHA-256 hashes. The four temporary transport parts and temporary apply workflow are absent from the published source tree.

All **seven regenerated native WAV files are byte-for-byte identical** to the previous main preview at `27f685172a19ab5cd8829da93195e91a01f6b09b`:

| Original WAV | SHA-256 |
|---|---|
| airborne-left.wav | `e6732e2474d889440454543baab108fe20ef0d25d98ba4fb8b5a43ac9df6efe8` |
| fine-texture-left.wav | `2976c714a84bf9a4c9b37860ad9d92a00ae46c13abba5f61d7bf99ce15b623b3` |
| press-left.wav | `76a37504ad39da50199e883317df1edb359704b2b2cadf36f5f4892003e7bf1d` |
| stroke-left.wav | `4c0e31424aac5b548046b751444074b9badd04f3e92e2574f8e919c276407bdd` |
| tap-right.wav | `7baa5a91cf8f44d8fa7eebed63ebc276b498a513a3e9c3c9420342dcd7d58a98` |
| unsteady-stroke-left.wav | `c871de37898b158a911f404d9a60a418704f6b366ad61ba58b537fb00da900e9` |
| wet-stroke-left.wav | `cd1832a61e9033dbbf5632cdd2604de286b2f0df42b998a07b320037a92069f3` |

This is preservation evidence, not a new acoustic-quality score. All six native source files and seven shipped scene definitions remain unchanged. There was **no newly spawned LLM-subagent review and no human listening assessment**. See [IMPLEMENTATION_AUDIT.md](../../../docs/IMPLEMENTATION_AUDIT.md) for the source-based findings and unresolved scientific requirements.

The artifact contains `dist/`, `outputs/review/Ku100-Research-Preview.html`, original WAVs, numerical reports, tests and the exact tested Git source bundle. CI artifacts expire; this receipt and the historical research reports are stored in Git. No raw performance recording or sensor trace is published in the site. Generated native example audio is intentionally included in the preview.

Any subsequent main-branch CI result must be checked separately at its actual commit. Browser tests and an artifact upload do not establish that GitHub Pages has deployed.
