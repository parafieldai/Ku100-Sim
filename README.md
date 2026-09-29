# Parafield — KU100 Contact Physics Lab

A **native C++17 physical research renderer** with a separate static browser viewer. The renderer computes fresh contact forces, structural vibration, chamber pressure, duct transmission and vent radiation. It exports stereo Float32 WAV, physical traces and a portable `.ku100.json` bundle. The viewer plays that exact export and shows its state.

**Current status:** a tested generic physical fixture with a measured KU100 airborne receiver. It is **not a calibrated KU100 or 3Dio digital twin**, a complete liquid simulation, or a demonstrated realistic ASMR generator. The research identifies concrete limits, including inadequate high-frequency contact content and missing force-to-microphone calibration. Numerical stability and source-data integrity do not establish perceptual fidelity.

This repository is the source of record. Use Git commits and branches for changes. Generated renders, downloaded archives and user reference recordings are excluded from Git and the publication build.


## Quality research update

The main engine now includes an optional passive **frequency-dependent viscous air-loss model**, independently checked against the circular-tube Bessel solution. New wavelength controls expose the source's excitation bandwidth. Per-ear, per-band convergence checks explicitly mark weakly excited bands as unassessed, rather than inferring full-band quality from a low-frequency-dominated global score.

See [quality changes and remaining limits](docs/QUALITY_UPDATE.md), [equations and validation](docs/VISCOUS_LOSSES.md), and [HF/Kaggle/paired-data research](docs/DATASET_RESEARCH.md). Use `scenes/unsteady-stroke-left.json` for the new 256-mode experiment. The fine-texture example is an uncalibrated sensitivity study, not measured tongue texture.

Successful native CI publishes **`ku100-verified-<commit>`** in the run's Artifacts section. It includes `outputs/review/Ku100-Research-Preview.html`, original WAVs, evidence, and the hosted-viewer directory. The HTML opens directly without a server. GitHub authentication is needed for a private repository's Actions artifacts. The public Pages workflow uses only the tested static viewer and runs separately; it never publishes reference recordings or repository source archives.

## Run a native render

The validated environment is Linux with Python 3.12, a C++17 compiler (`g++` or `clang++`), and the pinned Python dependencies. Node 22 is used for viewer checks. The native solver has no third-party C++ dependency.

```sh
python -m pip install -r requirements.txt
python scripts/build_native.py
python scripts/render.py --scene scenes/stroke-left.json --out outputs/my-stroke
```

Choose a new output directory for each render. Existing results are not overwritten. The wrapper verifies the executable against its build receipt, checks the exported audio and trace, and publishes the output directory only after verification.

| File | Meaning |
| --- | --- |
| `render.wav` | Stereo 48 kHz Float32 output with the scene's declared common capture gain |
| `cavity-pressure.wav` | Both generic chamber pressures, samples in Pa; not a listening-normalized recording |
| `airborne-source.wav` | Separate vent-source pressures at the fixed 0.25 m reference, before measured receiver processing |
| `trace.csv` | Actual native forces, indentation, pressure, work, energy and loss |
| `scene.json` | Complete resolved SI-valued parameters |
| `native.json`, `render.json` | Numerical checks, physical-regime diagnostics and provenance |
| `render.ku100.json` | The exact listening WAV plus scene, state, geometry, metrics and hashes in one viewer file |

No recorded performance is decoded or replayed during synthesis. Deterministic surface texture changes contact geometry in metres; no noise is added directly to the audio. Two physical channels are computed, without arbitrary ear leakage or per-ear normalization.

### Measured airborne receiver

```sh
python scripts/prepare_ku100.py --download
python scripts/render.py --scene scenes/airborne-left.json --out outputs/my-airborne
```

Preparation checks pinned hashes of the authors' releases and reproduces their channel orientation before creating `data/ku100_bank.bin`. Rendering verifies that bank against the tracked manifest. The five measured source radii are **0.25, 0.5, 0.75, 1 and 1.5 m** from head centre, with 360 horizontal azimuths. Intermediate radii use approximate coefficient interpolation; extrapolation and elevation are not implemented.

## Inspect and play the result

```sh
python scripts/prepare_ku100.py --download
python scripts/generate_examples.py
python scripts/build_site.py
python -m http.server 8080 --directory dist
```

Open `http://localhost:8080`. Load an example or import `render.ku100.json`. Rotate the generic fixture, inspect pressure/force/energy, seek the audio and download its original WAV. Playback attenuation is common to both ears and does not alter the export. Import stays in the browser.

The scene editor exports input for the native CLI. Editing controls leaves loaded audio associated with its original scene until a new native render is imported. The viewer prominently flags exports that fail the physical-regime screens.

The example capture chain uses nominal sensitivity 20 mV/Pa, gain 20 dB and 2 V full scale. The very quiet airborne vent example declares **90 dB ideal gain** in its scene. This supports an audibility experiment, not a prediction of real preamp noise performance. Electronics self-noise, capsule overload, microphone high-pass response and absolute target-device calibration are not modeled. Float32 files preserve overloads; reports count samples beyond full scale instead of hiding them with a limiter or normalization.

## Physical model

The source is a **generic bilateral fixture**: two elastic plates, two air chambers, a distributed connecting duct and two outward vents. This geometry is an explicit experiment, not an assertion about KU100 internal construction.

1. A prescribed actuator engages a fixed finite contact footprint. Seeded analytic microtexture translates through it during a stroke.
2. A unilateral nonlinear spring, closing-only damping, regularized friction and optional Newtonian film forces couple to the vibrating plate. Forces are solved with structural/acoustic feedback.
3. Mass-normalized Mindlin plate eigenvectors include bending, transverse shear and rotary inertia. Paired force/velocity coupling preserves interface work.
4. Plate motion and chamber pressure interact reciprocally. A one-dimensional finite-volume duct transmits pressure and volume flow between chambers.
5. Vents have air inertance, resistance and a passive equivalent pulsating-sphere radiation impedance. Radiation loads the source and supplies separate airborne observations.
6. Contact mode observes both chamber pressures. Airborne mode sends one synthesized vent source through measured KU100 responses at a stated external position.

Linear states use implicit midpoint integration; the nonlinear spring uses a discrete potential gradient. Stored energy, actuator work and dissipation are accumulated independently, without an energy clamp. Default integration is 192 kHz, followed by a causal anti-alias filter and 48 kHz export. Receiver/filter tails and processing delays are retained and reported.

Read [the equations and assumptions](docs/PHYSICS.md) and [the scientific claims audit](validation/research-audit.md).

### Why the default load is 0.01 N

Review found that the initial 0.6 N experiment deflected this soft plate beyond the linear model's assumptions and drove excessive vent/duct flow. Lowering playback gain could not fix that error. The default is now a gentle **0.01 N nominal preload**. The renderer reports a conservative displacement bound over the plate, displacement/thickness, Mach and Reynolds numbers, and flags exceeded small-deflection/low-speed/laminar screens.

Passing these screens does not check every strain, turbulence condition or constitutive approximation. Ordinary touch on a soft pinna requires a calibrated nonlinear geometry/material model.

### Remaining limits

The default 128 modes span approximately **20.8–1167.8 Hz**. A 48 kHz export does not make this a spatially resolved 20 kHz structural model. Most contact energy remains below 500 Hz; weak upper bands cannot support a convincing bandwidth-convergence claim.

The fluid branch models squeeze/shear-film forces. It does not solve a liquid free surface, saliva, capillary bridges, cavitation, bubbles, adhesion or changing contact area. Wetness changes force and dissipation; it does not trigger invented sound events.

The duct is not a measured KU100 cross-head path. Chamber pressure is not demonstrated capsule pressure. No KU100/3Dio scan, measured viscoelastic parameter set or instrumented contact recording has calibrated the model. No human listening assessment has certified the output.

## Reproducible evidence

```sh
python scripts/prepare_ku100.py --download
python -m unittest discover -s tests -v
npm --prefix web ci
npm --prefix web test
python scripts/validate_physics.py
python scripts/generate_examples.py
python scripts/build_site.py
npx --prefix web playwright install chromium
node scripts/browser_e2e.mjs
```

Native checks cover passivity, mirrored excitation, silence, controls, mode/time-step/duct refinement and invalid regimes. Receiver tests use independent NumPy/SciPy calculations for convolution, decimation, fractional delay, interpolation and exports. Pipeline tests exercise actual C++ rendering, strict inputs, source identity, hashes and atomic output. Browser tests exercise the built site, original WAV download, import, scene editing, playback and mobile layout.

| Evidence | What it establishes |
| --- | --- |
| [Physics convergence](validation/physics-convergence.json) | Numerical behavior for a fixed input, source/compiler hashes and weak-band flags |
| [Independent physics audit](validation/physics-audit.md) | Independent checks and remaining physical/numerical assumptions |
| [Receiver audit](validation/receiver-audit.md) | C++ data/DSP/export correctness, including the fixed negative-epsilon indexing defect |
| [Pipeline audit](validation/pipeline-audit.md) | Native render/export correctness and reproducibility |
| [Original data orientation](data/orientation-check.json) | Named MIRO channels reproduce SOFA coefficients despite conflicting position metadata |
| [Measured-bank validation](data/validation.json) | Extraction, gains, angular holdout and distance holdout |
| [Independent SADIE comparison](data/sadie-benchmark.json) | Disagreement between measured KU100 sessions; not a contact-equivalence score |
| [Input archive review](docs/INPUTS_AUDIT.md) | What uploaded ZIPs/documents contain and which earlier results reconstruct existing audio |
| [Integrated validation](validation/VALIDATION.md) | Final suite totals, real example levels, browser playback and sanitizer scope |

Angular holdout gives **0.43–0.46 dB median spectral RMS error**. Distance interpolation is less accurate: removing the 0.5 m circle gives **6.49 dB median error**. Both results are retained, not converted to a generic fidelity percentage.

The independent SADIE II KU100 session at 1.2 m differs by **2.72 dB median spectral RMS** after one common level offset, **4.17 dB frequency-dependent ILD RMS**, and **7.81 μs median correlation-ITD discrepancy**. Different measurement/processing chains contribute to these differences. Reproduce with `scripts/benchmark_sadie.py --sadie PATH_TO_D1_48K_24bit_256tap_FIR_SOFA.sofa` and the pinned source release in its report.

## Research and microphones

[MICROPHONES.md](docs/MICROPHONES.md) compares Neumann KU100, 3Dio Free Space/Free Space XLR and Free Space Pro II, including revision and noise-specification caveats. No 3Dio mode is labeled measured without its own transfer data. Body colour alone does not identify a capsule revision.

The implementation uses energy-accounting methods discussed by [Bilbao, Torin and Chatziioannou](https://arxiv.org/abs/1405.2589), vibration/contact feedback motivated by [Zheng and James](https://www.cs.cornell.edu/projects/Sound/mc/), and reciprocal structural/acoustic coupling. These papers support methods; they do not verify this fixture against a real microphone.

The [Arend–Neidhardt–Pörschmann measurements](https://zenodo.org/records/4297951) supply 1,800 horizontal direction/distance pairs, two ears and all 128 published taps. Corrected radius gains are applied once to both ears. No second inverse-distance gain, extra ear canal or duplicate head-shadow filter is added. The authors used analytical low-frequency extension around 200 Hz; those frequencies are not independent measured evidence for contact realism. Absolute pressure and absolute time origin remain uncalibrated.

## GitHub Actions previews and Pages

Every successful main CI run retains the tested site, original WAVs, numerical evidence and a server-free `outputs/review/Ku100-Research-Preview.html` in its `ku100-verified-<commit>` artifact for 14 days. Open the run under **Actions → Validate native renderer and viewer**, download its artifact, and open that HTML locally.

The **Publish viewer** workflow uses only the exact artifact from a successful main-branch CI run in this repository. It supports an authorized public Pages website without making the private repository or user recordings public. It requires Pages to be configured with **GitHub Actions** as its source; unavailable Pages produces a recorded availability result and a skipped deployment, not a claimed live site. A manual run takes an existing successful main CI run ID. No live website is guaranteed by committing the workflow.

[Research and evidence index](docs/RESEARCH_INDEX.md) collects the physics, microphone/data studies, historical reports and durable numerical evidence. [The document-to-implementation audit](docs/IMPLEMENTATION_AUDIT.md) records the latest review scope, corrected input-contract mismatches and remaining scientific limits. The separate `benchmarks/contact-coupon` remains a benchmark, not the application renderer.

## License and attribution

Original code and explanatory documents use the [MIT license](LICENSE). Measured KU100 data and derivatives retain the source payload's **CC BY-SA 3.0** notice, separately from code. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [data/LICENSE_DATA.md](data/LICENSE_DATA.md). User recordings and third-party head geometry are not included in the renderer or site.

Neumann, KU100 and 3Dio identify the researched hardware. This project is independent and is not manufacturer certified.
