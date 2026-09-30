# Empirical burst source — reproducible, deliberately nonphysical comparator

## Data and fitting

Source input is the user's stereo 44.1 kHz WAVs. The right profile fits chapter 03
at 0–50 and 70–120 seconds (325 detected acoustic events). The left profile fits
chapter 04 at 0–82 and 102–184 seconds (456 events). Windows are analysed separately;
concatenating them would invent boundary transients. These counts are detector
outputs, not annotated physical events or distinct interactions.

Detection uses a 100 Hz high-pass analysis channel, 4 ms RMS blocks, a fixed
smoothing kernel, peak distance/prominence, and a bounded 40–300 ms event duration.
A detected peak is not evidence for a bubble, suction release, peel or tongue
motion. Details are executable in `event_candidates`, not manually assigned.

For fitting only, audio is rationally resampled to 48 kHz and a 35 Hz high-pass is
applied to each event. Each event uses its near-channel RMS as one common scale
for both ears. Power is pooled into 16 event-life phases and 66 frequency knots
per ear. Only aggregate spectral envelopes, duration/rate/RMS statistics and
provenance are exported. There is no stored source waveform, original phase
sequence, per-event parameter bank or original event timeline in the runtime model.

**Limit:** equalized event contributions lose the relationship between an event's
absolute level, spectrum, and instantaneous left/right balance. A mean profile
cannot represent a mixture of strongly different local conditions. Replacing
phase by a minimum-phase construction also does not preserve real interaural
phase/coherence. Those limitations are observed in the comparison, not concealed
with fitted post-render ear gains.

## Runtime

Each phase/ear envelope becomes a causal 1,024-tap minimum-phase FIR derived with
a real-cepstral construction at a 2,048-point transform size. A shared bank scale
is used for both ears. A freshly sampled renewal pulse train drives triangularly
crossfaded phase filters inside each newly generated event. Event durations and
requested acoustic RMS values are sampled from aggregate fitted distributions;
event onsets are newly generated, not replayed.

The 1,500-pulse/second micro-excitation density, initial attack pulse, distribution
shapes/clamps and gamma timing regularity are **authored acoustic assumptions**.
They are not measured bubble counts, contact forces or saliva dynamics. Per-event
RMS adjustment is explicit sound-model gain, and a fixed 0.1 common digital scale
provides headroom. A render exceeding full scale is rejected rather than limited
or independently normalized by ear. The continuous negative control removes
macro-event grouping and time-varying event filters; it is not another reference.

The microphone-domain source already contains fitted recording/transmission
characteristics. Applying an additional KU100 HRTF would be an unjustified second
spatialization, so this comparator does not do so. The existing native fixture and
its separate measured airborne route are unchanged.

This is signal modeling, not full Spectral Modeling Synthesis, a neural decoder,
a contact solver, or a calibrated pressure field. Compare Serra and Smith's
[signal-modeling distinction](https://mtg.upf.edu/node/251); no claim is made that
the current simplified model implements their complete algorithm.

## Reproduce

```bash
python scripts/render_burst_source.py --model models/burst-right.json \
  --out outputs/new-acoustic-test --seconds 6 --seed 90293
python scripts/build_target_study.py
python scripts/assess_target_study.py
```

Outputs are Float32 stereo WAV plus manifest, original audio/source/model hashes,
generated event timing and explicit nonphysical labels. Runtime needs the pooled
model and NumPy/SciPy, not the reference WAVs. Repeat requests are byte-reproducible
in the tested environment; universal cross-version/platform byte identity is not
promised. Different seeds produce different waveforms, but that alone is not a
proof of perceptual diversity or generalization.

Refitting is a separate explicit command. It requires original private source
files and refuses to overwrite the chosen model. Keep old models and their
negative results in Git rather than silently replacing frozen evidence.

## Listening conditions

The page offers original digital levels and a common stereo-RMS match at -26 dBFS.
One scalar is applied to both ears of a clip; it is not independent ear matching
or perceptual loudness matching. A static common peak guard at amplitude 0.5 is
reported when it changes the requested playback gain. Additional headphone
attenuation defaults to -12 dB. Downloads preserve original generated samples or
the exact reference crop, not the gain-adjusted preview.

Candidates are randomly ordered and identified only after reveal. The recording
reference is explicitly identified. A listener chooses an initially empty rating
and can record notes. Result JSON records source/crop/candidate identities,
comparison gain, actual player volume/mute/rate, and whether identity was hidden.
Automated UI tests enter a **test observation**, not a real listener result.

The page does not promise matched actions or sample alignment between the source
recording and the fresh event realization. It contains no synthesized anatomy
animation implying motion that was never measured or simulated.
