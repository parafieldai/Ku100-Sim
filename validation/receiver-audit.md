# Independent native receiver audit

The audited receiver passes **19 unittest methods, with zero failures, errors or skips**. The run includes the prepared five-radius KU100 bank. The full executed log is [receiver-unittest.txt](receiver-unittest.txt); exact source, test and bank hashes, environment and numerical observations are in [receiver-audit.json](receiver-audit.json).

The test harness compiles `native/receiver.cpp` and a test-only adapter, `tests/receiver_probe.cpp`, directly with g++ and no physical-core linkage. NumPy and SciPy supply independent numerical references. The test signals are synthetic; no reference performance recording is loaded or played.

Reproduce from the repository root:

```sh
python -m unittest discover -s tests -p test_receiver.py -v
```

The recorded run used Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 and g++ 13.3.0. Compilation produced no warnings. The receiver source SHA256 at this run is `a5526aee4b79386272fa3ec05236d8a5228c3f48ebfbccfc5f27e9559f17eceb`; the bank SHA256 is `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712`.

## Defects and corrections verified

The independent audit found an angular boundary defect. For a negative azimuth extremely close to zero, such as −1e−14°, adding 360 to the negative remainder rounded to exactly 360. The old index calculation then addressed direction 360. At the first radius it read the next ring; at the final radius it read beyond the coefficient vector. In the distinguishable synthetic bank, the first left coefficient changed from 0.125 at 0° to 0.25 at −1e−14°, although the responses should agree to rounding precision. The original receiver source had SHA256 `c120a5bf0c09b6911aeea8e2ade041face88f434f171188ff8cfa4a9e857041e`.

The implementation owner corrected the wrapped angle to zero when its rounded value reaches 360. The dedicated regression covers −1e−15° and −1e−14° at both synthetic radii; all four cases now return the correct samples exactly.

Before the final audit, the implementation owner also made the 63-tap fractional-delay filter retain its fixed 31-sample processing delay at integer delays. The tests confirm that zero, integer and fractional delays share that time convention. Crossing a one-sample boundary by ±1e−8 samples changes the waveform by approximately 1e−8, without a 31-sample jump.

## Coverage and observed errors

| Operation | Independent reference or invariant | Recorded result |
| --- | --- | --- |
| Binary bank loading | Explicit little-endian Python encoder; every dimension carries distinguishable coefficients | Exact responses at 10 selected synthetic measurements; malformed magic, shape, radius, finite-value, truncation and trailing-byte cases rejected |
| Measured bank loading | Independent NumPy binary decoder | All 128 taps in both ears match exactly at 0°, 90°, 180°, 270° and 359° on each of five radii: 25 complete stereo-response comparisons |
| Angular and radial interpolation | Separate float64 interpolation calculation, including wrap and log-radius weights | 35 comparisons; maximum absolute coefficient error 5.56e−17 |
| Convolution | `numpy.convolve`, including empty operands and nonzero last tail samples | Maximum absolute error 3.56e−15; full `N + M − 1` length retained |
| Decimation | SciPy `firwin` with a Kaiser window and `upfirdn`, at 48/96/192/384/768 kHz | 20 comparisons; maximum absolute sample error 2.23e−15; causal tail retained |
| Fractional delay | NumPy sinc with SciPy's independent Kaiser window | Seven delays; maximum sample error 4.45e−16; fixed 31-sample processing latency and full tail |
| Delay frequency response | Analytic complex exponential at 100 Hz, 1 kHz, 10 kHz and 18 kHz | Maximum complex response error 1.44e−5 for a 4.375-sample requested delay plus 31 processing samples |
| Airborne composition | Independent fractional delay followed by per-ear NumPy convolution | Maximum absolute sample error 1.39e−17; corrected bank amplitude preserved without another inverse-distance gain |
| Stereo WAV | Independent RIFF chunk decoder and SciPy WAV reader | Exact float32 payload, left/right order, polarity, sample rate and frame count; values above full scale remain unchanged |

For 192-to-48 kHz decimation, the measured steady-state sine amplitudes were 0.99999798 at 1 kHz and 0.99999811 at 10 kHz. A unit-amplitude 30 kHz input left 7.10e−7 RMS-equivalent output amplitude; 70 kHz left 9.72e−8. These are specific tested tones, not a measured continuous stop-band specification.

The bank loader rejects extrapolation beyond its measured radius range and nonfinite coordinates. It also accepts a valid single-radius bank without a zero-denominator radial interpolation. Invalid rates, nonfinite samples, excessive delays, inconsistent WAV channels and float32 overflow are rejected.

## Time and amplitude interpretation

For integration rates above 48 kHz, causal decimation contributes 64 samples at 48 kHz, or 1.3333 ms. At 48 kHz input the decimator is the identity and contributes no delay. Airborne propagation adds the requested distance divided by sound speed, plus the fractional-delay filter's 31 processing samples, or 0.6458 ms. The published HRIR waveform and its time origin remain intact. These distinct terms must remain visible in rendering metadata; this audit does not establish an absolute measured acoustic flight time from the HRIR bank.

The native airborne path applies the bank coefficients as stored. The bank preparation owns the authors' distance corrections and channel-orientation provenance, documented in [the data README](../data/README.md), [the bank manifest](../data/manifest.json) and [the orientation check](../data/orientation-check.json). This audit verifies the native reader and signal operations against that prepared binary; it does not independently re-estimate those physical corrections.

## Limits

Passing these tests establishes implementation behavior for the listed inputs and rejects the exercised invalid cases. It does not show that intermediate-radius interpolation reproduces a physical measurement. The bank's separate holdout report records substantial radial interpolation error, particularly when the 0.5 m circle is withheld. Prefer measured radii for experiments that require directly measured transfer responses.

The receiver test does not execute the contact solver, validate force-to-pressure transfer, identify KU100 internal geometry, calibrate pascals to microphone voltage, or assess perceptual resemblance to a recording. Those claims require separate evidence. No loudness normalization, gain matching, reference waveform mixing or listening assessment was used in this audit.
