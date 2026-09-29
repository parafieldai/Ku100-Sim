# Measured airborne KU100 receiver bank

`ku100_bank.bin` is a reproducible derivative of the authors' [Zenodo release 4297951](https://zenodo.org/records/4297951). It contains measured airborne responses, not performance recordings or contact impulse responses. The original files are downloaded outside this repository. See [LICENSE_DATA.md](LICENSE_DATA.md), [manifest.json](manifest.json), [orientation-check.json](orientation-check.json), and [validation.json](validation.json).

From the repository root, with the Python requirements installed:

```sh
python scripts/prepare_ku100.py --download
```

To use existing originals, pass `--source-dir /path/to/originals`. The default cache is `~/.cache/ku100-sim/4297951`. All five source circles, the gain correction, the original paper, and the MIRO orientation evidence are pinned by SHA256. A changed download fails rather than silently changing the bank. Preparation requires NumPy, SciPy, and h5py; the C++ receiver requires only the resulting bank.

The native bank is 1,843,264 bytes. Its SHA256 is `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712`.

| Byte offset | Encoding | Value or meaning |
| ---: | --- | --- |
| 0 | 8 ASCII bytes | `KUHRIR01` |
| 8 | little-endian uint32 | 48000 samples/second |
| 12 | little-endian uint32 | 5 radii |
| 16 | little-endian uint32 | 360 azimuths |
| 20 | little-endian uint32 | 128 taps |
| 24 | five little-endian float64 | 0.25, 0.5, 0.75, 1.0, 1.5 metres |
| 64 | little-endian float32 | C-order `[radius][integer azimuth][left,right][tap]` |

All 128 published taps are retained. Each circle is multiplied once, in both ears, by the authors' corrected factor: `1, 0.33, 0.25, 0.16, 0.095`. These are not inferred inverse-distance gains. No normalization, extra `1/r`, EQ, sample alignment, additional window, or resampling is applied. Float64-to-float32 conversion is the only precision change. These responses do not establish absolute pressure sensitivity.

Azimuth is listener-relative: 0° front, 90° left, 180° rear, 270° right; all elevations are zero. Radius is measured from the head centre, not from the ear surface. The valid measured range is 0.25–1.5 m. There are no contact-gap or elevation measurements in this bank.

The SOFA `ReceiverPosition` signs disagree with the channel convention. We resolved routing through the separately published MIRO files: their explicitly named **Left Ear** and **Right Ear** responses, with the authors' `getIR` window, reproduce every archived SOFA coefficient (maximum error zero). The accompanying `miroCoordinates` defines 90° as left. Channel order is retained; the inconsistent source metadata is preserved in the manifest. The older SOFA mirror has unwindowed responses and differs numerically, so it is not silently substituted.

Preparation independently reopens each SOFA, decodes the binary header/payload, and checks every coefficient against the corrected source. It also reports per-ear gain fits and cardinal ILD/ITD. Separate holdout measurements remove all odd-degree directions, reconstruct them from even neighbors, and compare against the 900 withheld directions. Median per-ear spectral RMS error is 0.43–0.46 dB over 200 Hz–16 kHz. This assesses interpolation across 2° gaps; it does not measure errors at the runtime's unmeasured fractional degrees.

Leaving out a complete interior radius exposes a larger limitation of log-radius coefficient interpolation: median spectral RMS error is 6.49 dB at the withheld 0.5 m circle, 2.41 dB at 0.75 m, and 1.33 dB at 1 m. These are observations, not pass criteria. Prefer measured radii when reproducibility matters. Interpolation does not confer measured fidelity at intermediate distances. Broadband correlation ITD occasionally switches correlation peaks; exact metric definitions and maxima are retained in the JSON, rather than hidden behind a median.

The [original paper](https://zenodo.org/api/records/4297951/files/Arend_TMT2016.pdf/content) describes analytical low-frequency extension at 200 Hz, source-response compensation, and limitations of close-range measurements. Accordingly, these data cannot independently validate low-frequency contact mechanics. Numerical extraction and interpolation checks do not establish that simulated rubbing, deformation, fluid contact, or bilateral internal transmission matches a KU100. See [MICROPHONES.md](../docs/MICROPHONES.md).
