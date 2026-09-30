# Target-first reset: what is and is not implemented

The original handoff asks for convincing freshly generated tongue/wet-ear sound.
It explicitly rejects interpreting shaped noise, a numerical pass, or a polished
website as the requested result. The earlier native generic plate/chamber/duct
model does not establish that result. Its equations are unchanged in this update.

## The new deliverable

A reference-first listening study now compares four **exact six-second excerpts**
from the user's supplied stereo WAVs with six generated comparisons: two new right
seeds, one new left seed, a continuous-source negative control, and matched-duration
right/left generic-fixture baselines. The fitting and synthesis implementation is
in `ku100sim/burst_source.py` and the documented command-line scripts.

This is a falsifiable **empirical microphone-domain acoustic experiment**. It is
not a new physical tongue, saliva, artificial-ear or contact-microphone model.
Controls are acoustic event rate, seed and excitation stop time—not force, speed
in metres per second, liquid quantity or wetness. The physical meaning of the
source bursts is unverified. Do not promote this implementation into the main
physical renderer merely because its output has more high-frequency content.

The public build includes only generated WAVs, reference hashes/measurements and
the comparison UI. A user can load the original WAVs locally: the page validates
whole-file hashes, takes the declared sample interval and preserves both channels.
There is no upload endpoint. A separately packaged private HTML includes the
actual reference crops for immediate listening; **never publish that private file**.

## Reference and split identities

| Reference | Supplied-file interval | Role |
|---|---|---|
| Chapter 03, right-labelled | 57–63 s | Excluded from the new right-model fitting windows |
| Chapter 05, right-labelled | 64–70 s | Separate recording not fitted by this model |
| Chapter 04, left-labelled | 89–95 s | Excluded from the new left-model fitting windows |
| Chapter 06, left-labelled | 51.5–57.5 s | Separate recording not fitted by this model |

All four intervals were previously inspected. They are **not newly blind held-out
validation**, and file identity does not establish independent sessions. Device
model, gain/filter chain, actual physical action and force remain unverified.
Chapter 02 is labelled mixed mouth/objects/reverb and is not treated as isolated
wet-ear evidence. Exact source/crop hashes and metrics are in
`validation/target/reference-targets.json`.

## Measured failures, not a winner declaration

The generated right source has about 35.43 dB of right-over-left RMS separation;
the selected chapter-03 reference has about 38.52 dB, whereas the matched generic
fixture gives about 3.48 dB. That narrows **one aggregate spatial descriptor**.
However, the source places about 25.35% of its near-ear audio-band power in
1–4 kHz versus about 0.59% in that reference crop. It is not a spectral match.

The new left profile gives about 37.85 dB left-over-right, versus 8.36 dB and
6.45 dB in the selected chapter-04 and chapter-06 intervals. The pooling does
not preserve their local bilateral behavior. The continuous negative control
can also appear competitive on individual summary statistics: that is why one
number must not decide acceptance.

The reference crops themselves differ: chapter 04 puts roughly 0.53% of its
near-ear audio-band power in 1–4 kHz, while chapter 06 puts roughly 74.08% there.
An unconditional pooled “wet” profile is not an adequate description of this
variation. These are measured descriptor differences, **not estimates of physical
force, wetness, or listener realism**. The current experiment remains rejected
as a completed target model; listening results are unfilled until a person submits
them. No human listening assessment has been performed by this implementation.

Run `python scripts/assess_target_study.py` to obtain all discrepancies.
`--require-target` intentionally returns exit code 2: the product acceptance gate
is not met. Ordinary CI may verify this research tool without implying that the
product gate passed.

## Handoff-to-implementation map

| Requirement | Current result |
|---|---|
| Use the supplied sound as the target | Exact local reference crops, hashes, separate stereo descriptors and immediate private comparison |
| Fresh audio, not runtime clip retrieval | New pooled parameter model with generated pulses/timing; original performance files absent at runtime |
| Listen before attractive animation | Audio-only comparison; existing geometry stays on the separate engineering page |
| Preserve the quiet ear | Original channel ratios retained in reference import and shared-gain comparison; per-ear failures exposed |
| Rolling, peel/release, changing wet contact and history | **Not physically implemented by the new source; not solved by the old fixture** |
| Measured physical control mapping | **Not established**; empirical controls use no physical-unit labels |
| Target-relevant listening acceptance | Tool implemented; observations initially empty; **not yet assessed** |
| Sound-related item/trigger research | 18 evidence-linked entries, explicitly separating primary target, controls and future items |

## What the failure changes about the next model decision

Do not respond by adding arbitrary per-ear attenuation, a loudness-to-force
conversion, or guessed “bubble” events. The acoustic source model needs a
joint account of event-level spectrum, amplitude, and bilateral behavior rather
than independent pooled averages. A sound described as a wet click may originate
at a contact interface, inside a mouth, or at a changing opening; a WAV and avatar
video do not resolve that ambiguity.

The smallest useful source-isolation experiment is a documented contact-free
mouth gesture versus actual contact, plus stationary hold and controlled
separation, recorded with the same raw stereo capture chain. This is a proposed
experiment, not an assertion that it already exists or a universal capture
standard. Only after that discrimination should a contact mechanism be assigned
and fitted. Material/force data and airborne HRIRs from unrelated experiments do
not jointly measure this missing source-to-two-microphone relationship.
