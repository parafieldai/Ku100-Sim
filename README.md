# Parafield — KU100 Native Contact Physics Lab

**A working C++17 reduced physical simulator and native-output web viewer. Not a calibrated KU100 or 3Dio digital twin. Wet-contact sound realism remains unvalidated.**

The waveform is generated from prescribed contact motion, nonlinear contact forces, elastic plate motion, reciprocal cavity/vent dynamics and radiation loading. It does not replay recorded mouth sounds. The browser displays native renders and synchronized telemetry; it does not pretend to run a live physics solver.

## Build and run

Requires CMake, a C++17 compiler, and Python for analysis/site tooling. Python dependencies are in `requirements.txt`.

```sh
python -m pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j2
python tools/run_scene.py examples/stroke.json --out outputs/stroke
python tools/run_scene.py examples/airborne.json --out outputs/airborne
python tests/verify.py
python tools/sphere.py
python tools/compare_receivers.py
python tools/build_site.py --out _site
```

Open `_site/offline.html` for self-contained playback, or serve `_site/` with a local HTTP server. The site contains four precomputed native scenes, raw Float32 WAV downloads, common-gain listening previews, physical telemetry and scene JSON export. Change the JSON and invoke the native runner to make a new scene. Output directories must be new; the renderer refuses overwrites.

The physical contact WAV contains modeled **pascals**, not calibrated microphone voltage or ADC dBFS. Start listening at low volume using the common-gain preview. The original physical WAV is unchanged.

## What is implemented

- Two assumed simply supported Kirchhoff-Love plates with a finite contact patch and explicit structural coupling.
- Hertz-type contact potential and a closing-only Newtonian squeeze-film approximation.
- Reciprocal pressure/structure, cavity/vent and radiation-memory coupling, with per-step work and energy accounting.
- Causal anti-alias filtering and 48 kHz stereo Float32 export with preserved filter tails.
- A separate measured KU100 airborne receiver route. One 25 cm / 90-degree stereo FIR is vendored with source hashes and attribution; tools can extract more exact measured directions.
- Independent continuous-ODE assembly, native sanitizer checks, a rigid-sphere Helmholtz benchmark, resolution diagnostics and an offline Chromium test.

This is **not** a full anatomical mesh, tissue model, free-surface saliva solver, capillary-bridge/adhesion model, calibrated internal dummy-head transmission, or simulated KU100/3Dio electronic chain. Artificial plate/cavity material values are assumptions, not manufacturer measurements. See [the equations](docs/PHYSICS.md).

## Evidence and unresolved limits

The local verification ran 67 native acceptance checks, 13 native component checks under sanitizers, per-channel measured-filter comparison, and seven offline Chromium checks. The source hash and measured values are recorded in [the evidence summary](research/summary.json).

Passing energy balance is not passing realism. The default 8x integration fails the strict late-decay reference target (12.87% final-state error); 64x reduces that particular error to 0.202%. Default 6x6 modes per ear still differ from the 12x12 waveform by 14.25%. The generated source remains heavily weighted below 250 Hz and is not an established match to the supplied wet-ear recordings. Read [the complete validation boundaries](docs/VALIDATION.md), including the retained failed tests.

Actual KU100 data were inspected at 25 and 50 cm; those airborne measurements do not validate direct contact. The unfitted ideal-sphere comparison has substantial high-frequency error and is not substituted for the measured response. Manufacturer research distinguishes KU100, 3Dio Free Space and current Free Space Pro II; none is identified solely from a recording label or the color black. See [research and sources](docs/RESEARCH.md).

## Git and deployment

This repository is the source of record. Use commits and branches, not successive source ZIPs. The original README-only commit remains in history; its earlier claims of complete source, a Mindlin engine, and 1,800 bundled receiver pairs do not describe this native implementation.

The verification workflow is committed. The observed cloud run failed before exposing job steps or logs, so cloud execution is **not** claimed as passed. The Pages workflow builds only the permitted viewer/output directory. Enable Pages with GitHub Actions as its source, then run **Publish native-output viewer** after the organization's workflow execution issue is resolved. No repository-visibility change is required or performed here. A workflow file alone is not proof of a live website.

## Licenses

Original code is MIT. The measured receiver derivative retains its source-file CC BY-SA 3.0 notice separately; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Raw user performance recordings are not published. No manufacturer affiliation or certification is claimed.
