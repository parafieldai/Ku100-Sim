# Native render pipeline audit

## Result

**17 tests passed; 0 failures, 0 errors, 0 skips.** The suite took 6.686 seconds
including its native build and temporary renders (7.353 seconds for the runner
including imports). The measured KU100 bank was present and its integration
case ran; this was not a bank-free or mocked renderer test.

The audited boundary is:

1. Strict scene JSON loaded by Python.
2. A locally compiled C++17 executable identified by its build receipt.
3. Native physical state, pressure stems, trace and stereo Float32 WAV output.
4. Python verification, canonical scene, metrics and portable render bundle.
5. Acceptance of that real generated bundle by the static publication validator.

The suite is [tests/test_pipeline.py](../tests/test_pipeline.py). It uses
`scripts/build_native.py` and invokes the actual `scripts/render.py` CLI for
successful renders and error-path checks. SciPy independently decodes the WAVs.
All executable copies, scenes and audio outputs are temporary. No network
request, reference-recording playback or live provider was involved.

## Observed results

Unless otherwise specified, the fixture is a **0.2-second left stroke**, texture
seed **411**, **128 modes per plate**, and the current **0.01 N** default load.
The declared capture settings were 20 mV/Pa, +20 dB and 2 V full scale, giving
one common **0.1 digital units/Pa** scalar. This is the nominal mapping described
by the program, not an independent pressure calibration of a KU100 capsule.

| Check | Observed result |
|---|---|
| Native build | Real g++ C++17 build succeeded; executable and all native source hashes matched the receipt |
| Contact export | 9,728 frames, 48 kHz, two Float32 channels; finite samples; causal decimator tail retained |
| Contact digital levels | RMS L/R −10.9187 / −16.0587 dBFS; peak L/R −1.6818 / −10.3831 dBFS |
| Capture equation | Each exported channel matched its raw cavity-pressure stem multiplied by the declared common scalar, within Float32 rounding |
| Repeated scene | `render.wav`, both pressure/source WAVs, `trace.csv`, `native.json` and `scene.json` were byte identical |
| Half-load control | Changing 0.01 N to 0.005 N changed stereo waveform L2 norm by 53.3164% relative to baseline; reported peak normal force changed from 0.0220600 to 0.0103221 N |
| Left/right mirror | Channel-swapped contact waveforms were exactly equal at Float32 precision; no alignment or level matching was applied |
| Silence | All samples in all three WAV files were exactly zero; work, dissipation and final energy were zero; RMS/peak dB fields were JSON `null` |
| Capture overload stress case | +100 dB capture versus +20 dB gave the declared common factor of 10,000; 17,804 samples exceeded magnitude 1 and were retained, with peak magnitude 8,239.7129 |
| Capture isolation | Both raw source/pressure stems and the trace stayed byte identical when only capture gain changed; interaural level difference was preserved |
| Measured airborne route | Actual 0.5 m, 90° bank response and generated left vent source produced 9,986 output frames, retaining propagation/interpolator/HRIR tails |
| Independent airborne reconstruction | NumPy/SciPy convolution of the exported vent source, an independently assembled fractional-delay kernel and the measured bank matched the native result with **3.3547 × 10⁻⁸ relative L2 error** |
| Airborne digital levels | RMS L/R −110.3560 / −115.7325 dBFS; no hidden gain was added to make the airborne route match the contact route |
| Portable bundle | Copied bundle alone decoded to the exact WAV bytes and sample values; embedded audio SHA-256, canonical-scene SHA-256 and native source/build identity matched |
| Trace timing | Bundle time equaled simulation time minus the first integration sample time plus the declared processing/propagation latencies |
| Publication boundary | The actual generated bundle passed `scripts.build_site._validate_bundle` |

The capture overload case is an export stress test. Its samples were never
played. The test establishes that the Float32 file preserves over-full-scale
values rather than silently clipping or normalizing them.

## Rejection and preservation checks

The suite checks **32 canonical-scene rejection cases**, **7 invalid JSON
cases**, **10 structured Python CLI rejections**, and **10 native CLI
rejections**. Some are deliberately repeated at more than one boundary.

Cases cover malformed JSON; duplicate top-level, nested and escaped-equivalent
keys; unknown fields; unsupported actions and sides; `NaN`, `Infinity` and an
overflowing exponent; an integer too large for a floating-point conversion;
booleans used as numbers; strings used as numbers; fractional seed/sample-rate/
mode-count/trace-stride/duct-cell integers; unsigned seed limits; unsupported
integration rate; negative load; and invalid capture settings.

The Python CLI returns an error object and exit code 2. It does not publish a
partial output directory or leave its temporary staging directory behind.

Additional artifact guards passed:

- Both Python and native entrypoints refused an existing populated output and
  left every existing artifact byte unchanged. Python also refused an existing
  empty output directory.
- Missing bank data failed explicitly in airborne mode. Contact mode succeeded
  with an intentionally absent bank path.
- A truncated bank and a same-layout bank with one finite Float32 mantissa bit
  changed were rejected. The latter confirms identity checking against the
  verified source manifest, rather than only checking binary structure.
- An explicitly selected missing executable, executable without a build
  receipt, tampered executable, and receipt claiming stale native source
  hashes were rejected before a render was published.

## Defects found and resolved during integration

1. A huge but syntactically valid JSON integer could trigger an uncaught
   `OverflowError` in numeric validation. The scene owner changed it to the
   normal `ValueError` path. Both direct contract and CLI regression cases pass.
2. The renderer emitted embedded audio fields `mime`, `base64`, `sha256` and
   `channels`, while the static packager initially allowed only the first two.
   The packaging owner aligned the schema and added actual hash/channel
   checks. The regression uses a real native-generated bundle, not a hand-built
   stand-in.

No implementation files were changed by this pipeline audit. Its persistent
changes are the pipeline test file and this report.

## Source and artifact identity of this run

Compiler: `g++ (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0`.

| Identity | SHA-256 |
|---|---|
| Built native executable | `d68b7898dce73327e62f482fb7a245f09f465c7707ec5401c55786323ca9691c` |
| Combined native source map | `b5b39fec656bb091f297ae2af61330640a6253f1529943f9ce0d6c5843988fd2` |
| Contact fixture WAV | `455a9d37bdb907f8efef78b527de9e9e6c766929ecded33445f0266e11e45113` |
| Verified KU100 bank | `8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712` |

The combined source-map digest is SHA-256 of the sorted-key JSON encoding of
the receipt's native source hash mapping. The receipt covered these files:

| Source | SHA-256 |
|---|---|
| `native/main.cpp` | `5c9ff1d0e1da6e8416de83c937997220ae1b55407acacc1ddf770d22329289b4` |
| `native/physics.cpp` | `ac154b7743d680ea064614d456fe6822cc836716478a8596c6cf31fb5509e961` |
| `native/physics.hpp` | `db508ba431c32b9e648b358e373ce2f13b98d6892adb180f6a8a2ddad957b49f` |
| `native/receiver.cpp` | `a5526aee4b79386272fa3ec05236d8a5228c3f48ebfbccfc5f27e9559f17eceb` |
| `native/receiver.hpp` | `04a3535d5784c0bc1422486f081e735622e154c8d84bcf5340c3dc8fe53beb1f` |

Hashes identify this particular source/build/output, rather than promising
byte-identical floating-point audio across every compiler and CPU. The bundle
also records Git commit and working-tree modification state. Native hashes
specifically identify the C++ producer; they are not a claim that every Python
or web file has been included in that native source digest.

## Reproduce

From the repository root with the declared Python requirements and a C++17
compiler available:

```sh
python -m unittest discover -s tests -p test_pipeline.py -v
```

The measured-bank case needs `data/ku100_bank.bin` and its verified manifest.
If that bank is absent, the case explicitly skips; the audited run above had
**zero skips**. Local machine-readable observations and raw runner output from
this run are under the ignored `validation/local/` directory.

## Limits of this result

This is software/data-path validation on short scenes. It does not establish
the generic mechanics' correspondence to a human ear or KU100 construction,
absolute microphone calibration, wideband convergence, perceived wet-contact
realism, or long-duration stability. The independent mechanics and receiver
audits address their own numerical assumptions. The extremely different
contact and airborne digital levels are preserved and visible here; the tests
do not interpret equal or unequal loudness as a physical realism score.
