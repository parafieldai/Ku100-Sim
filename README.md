# Parafield — KU100 Contact Physics Lab

A browser-based research simulator that computes contact forces, elastic motion, cavity pressure and acoustic radiation, then applies measured Neumann KU100 airborne responses. Source code, assumptions, audits and deployment configuration are versioned together in Git.

**Status: a working, energy-accounted reduced physical model. It is not a calibrated full KU100 digital twin, and its wet-contact sound has not passed a realism assessment.** The limitations below are measured development findings, not a claim that passing software tests establishes recording fidelity.

## Run the simulator

Requires a recent Node.js runtime for checks; the website itself has no package dependencies or external executable resources.

```sh
npm test
python -m http.server 8080
```

Open `http://localhost:8080`, choose **Stroke**, **Press** or **Tap**, and click **Start render**. Use **Match listening level** if the physical output is quiet, then **Play**. The matching control uses one common gain for both ears, reports its adjustment and affects playback only. WAV downloads preserve the original Float32 samples; they are not normalized or clipped.

The **contact** route observes a generic local cavity plus the modeled airborne source through the measured KU100 transfer. The **airborne** route uses only the measured receiver path. Its radius control selects the five measured circles, not a contact gap.

Command-line rendering uses the same engine and receiver implementation:

```sh
npm run render -- --duration 4 --preset stroke --side left
npm run render -- --duration 4 --receiver airborne --azimuthDeg 270 --distanceM 0.5 --out outputs/airborne
```

Outputs are ignored by Git. No performance recording is shipped with the runtime, and rendering does not decode or replay a reference waveform.

## What is actually simulated

1. A smooth, prescribed actuator moves over a fixed analytic texture, expressed in metres.
2. Unilateral nonlinear contact, closing-only material viscosity, a Newtonian squeeze-film approximation, and regularized friction produce forces.
3. A rectangular Mindlin plate basis includes transverse shear and rotary inertia. Tangential traction acts at the upper surface and produces a bending moment, so friction can drive audible motion through the mechanics.
4. Plate motion, cavity pressure and vent flow exchange energy reciprocally. Pressure pushes back on the plate and the vent.
5. An equivalent pulsating-sphere radiation impedance stores near-field fluid energy and removes outgoing acoustic energy. Radiation therefore loads the source.
6. Separate local-pressure and airborne observations produce stereo output. The airborne observation uses 1,800 measured KU100 direction–distance pairs.

Every internal step accounts for actuator work, stored mechanical/contact/air energy, and material, contact, film, friction, vent and radiation losses. No corrective energy clamp is used. The waveforms arise from the solved pressure states, with no independent noise generator or authored bubble/event sequence.

Full equations, units, geometry assumptions and the discrete work identity are in [docs/PHYSICS.md](docs/PHYSICS.md).

## Evidence and known failures

The independent audits check the actual implementation using analytic energy identities, a separately assembled continuous ODE, a matrix exponential, Radau integration, frequency tests, fixed controls and byte-level receiver/export checks. Read [docs/NUMERICAL-AUDIT.md](docs/NUMERICAL-AUDIT.md) and [docs/CODE-AUDIT.md](docs/CODE-AUDIT.md). Machine-readable evidence is in `research/`.

The default model has **64 plate modes plus one in-plane shear coordinate**. Its retained structural eigenfrequencies span approximately **54–1070 Hz**. A 48 kHz output file does not establish a spatially converged 20 kHz structural simulation. On the audit trajectory, doubling the mode count changes the weak 500–2000 Hz pressure spectrum by about 22%; the higher band has too little energy to assess convergence reliably.

The default four-second run gives approximately **−39.07/−132.81 dBFS left/right RMS**, or **93.74 dB interaural separation**. The opposite ear contains only the very weak modeled airborne component. Internal-head transmission, the contact observation and the relative local/air calibration remain unmeasured. This is an explicit receiver-model failure for realistic bilateral contact, and it cannot be fixed with a shared listening gain.

About 97% of the selected-ear unweighted spectral power is below 250 Hz in that run. No human listening assessment, recording-source recovery or real contact calibration is claimed. [docs/RESEARCH-STATUS.md](docs/RESEARCH-STATUS.md) identifies the next physical experiments and implementation milestones.

### Numerical quality

Both quality settings retain the same physical modes. **Standard** integrates at 192 kHz; **High** integrates at 384 kHz. A causal low-pass FIR produces 48 kHz output while preserving its tail. Linear components use an implicit midpoint update; the nonlinear spring uses a discrete potential gradient. Lagged state-dependent dry/film damping makes those terms first-order in time. The distinction is tested and documented.

The source arrays and model parameters are validated. A solver owns a private parameter snapshot, so external mutation cannot invalidate cached impedances. Unknown controls are rejected. Monitor gain is intentionally absent from the physics parameters.

## Measured KU100 receiver data

The bundled bank is derived from the Arend–Neidhardt–Pörschmann circular near-field KU100 dataset: five distances, 360 horizontal directions, two ears and 128 taps at 48 kHz.

| Source radius | Published correction factor |
| ---: | ---: |
| 0.25 m | 1.000 |
| 0.50 m | 0.330 |
| 0.75 m | 0.250 |
| 1.00 m | 0.160 |
| 1.50 m | 0.095 |

The renderer applies each factor **once to both ears**. These are the authors' corrected distance gains; their later note warns that the original MIRO normalization entries omit varying preamplifier gains. An additional inverse-distance envelope is not applied to that same measured path.

The responses preserve interaural timing but do not establish absolute source flight time or pressure calibration. The renderer retains their processing latency and adds a common modeled propagation delay. It does not add another human ear canal, head-shadow filter or diffuse-field equalizer after the measured response.

See [assets/README.md](assets/README.md), the [dataset](https://zenodo.org/records/4297951), and the [author gain correction](https://audiogroup.web.th-koeln.de/FILES/NF_Datasets_Gains_infos.pdf).

## Repository and deployment

This repository contains the source of record; use commits and branches for further changes. Development renders and raw reference inputs are excluded from Git and the website build.

The included CI checks run the Node test suite. The Pages workflow builds a dedicated static directory containing only the simulator and its permitted explanatory assets. Pages activation and the resulting audience depend on the repository/organization's GitHub Pages settings; a committed workflow alone is not proof that a site has deployed.

## License and attribution

Original code and original explanatory documents use the [MIT license](LICENSE). The measured HRIR derivative separately retains the source-file **CC BY-SA 3.0** notice. Its different record-level license statement is documented, not silently resolved. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [assets/LICENSE_DATA.md](assets/LICENSE_DATA.md).

Neumann and KU100 identify the measurement hardware. This project is independent and is not a manufacturer-certified simulator.
