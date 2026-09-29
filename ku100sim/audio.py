"""Strict RIFF intake and channel-preserving numerical descriptors.

No alignment, per-ear normalization or recorded-waveform synthesis occurs here.
These are signal measurements, not perceptual or physical-equivalence scores.
"""
from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

import numpy as np


def read_wav(path: Path | str) -> tuple[int, np.ndarray]:
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Expected little-endian RIFF WAVE")
    if struct.unpack_from("<I", data, 4)[0] + 8 != len(data):
        raise ValueError("RIFF length does not match the complete file")
    pos, fmt, payload = 12, None, None
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("Truncated RIFF chunk header")
        key, length = struct.unpack_from("<4sI", data, pos)
        pos += 8
        end = pos + length
        if end > len(data):
            raise ValueError("Truncated RIFF chunk")
        if key == b"fmt ":
            if fmt is not None or length < 16:
                raise ValueError("Invalid or duplicate WAVE format")
            fmt = struct.unpack_from("<HHIIHH", data, pos)
        elif key == b"data":
            if payload is not None:
                raise ValueError("Multiple data chunks are unsupported")
            payload = data[pos:end]
        pos = end + (length & 1)
    if pos != len(data) or fmt is None or payload is None:
        raise ValueError("Missing WAVE format/data or chunk padding")
    encoding, channels, rate, byte_rate, align, bits = fmt
    if channels not in (1, 2) or not 8000 <= rate <= 768000:
        raise ValueError("Only mono/stereo WAVE at supported rates is accepted")
    bytes_per_sample = bits // 8
    if align != channels * bytes_per_sample or byte_rate != rate * align or len(payload) % align:
        raise ValueError("WAVE frame layout is inconsistent")
    if encoding == 3 and bits in (32, 64):
        samples = np.frombuffer(payload, dtype="<f4" if bits == 32 else "<f8").astype(np.float64)
    elif encoding == 1 and bits == 16:
        samples = np.frombuffer(payload, dtype="<i2").astype(np.float64) / 32768
    elif encoding == 1 and bits == 24:
        packed = np.frombuffer(payload, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = packed[:, 0] | (packed[:, 1] << 8) | (packed[:, 2] << 16)
        samples = ((values ^ (1 << 23)) - (1 << 23)).astype(np.float64) / (1 << 23)
    elif encoding == 1 and bits == 32:
        samples = np.frombuffer(payload, dtype="<i4").astype(np.float64) / (1 << 31)
    else:
        raise ValueError(f"Unsupported WAVE encoding={encoding}, bits={bits}")
    if not np.isfinite(samples).all():
        raise ValueError("WAVE contains non-finite samples")
    return rate, samples.reshape(-1, channels)


def dbfs(value: float) -> float | None:
    """Silence is undefined in dB, serialized as null rather than a false floor."""
    return 20 * math.log10(value) if value > 0 else None


def describe(rate: int, samples: np.ndarray) -> dict:
    if samples.ndim != 2 or samples.shape[1] != 2 or not len(samples):
        raise ValueError("Expected nonempty stereo samples")
    if not np.isfinite(samples).all():
        raise ValueError("Non-finite signal")
    n = len(samples)
    rms = np.sqrt(np.mean(samples * samples, axis=0))
    peaks = np.max(np.abs(samples), axis=0)
    # Sum squared FFT magnitudes with proper one-sided weights (Parseval).
    frequency = np.fft.rfftfreq(n, 1 / rate)
    spectrum = np.abs(np.fft.rfft(samples, axis=0)) ** 2
    if n % 2 == 0:
        spectrum[1:-1] *= 2
    else:
        spectrum[1:] *= 2
    bands = [(0, 200), (0, 250), (200, 500), (500, 2000), (2000, 8000), (8000, 20000)]
    total = spectrum.sum(axis=0)
    fractions = {}
    for lo, hi in bands:
        energy = spectrum[(frequency >= lo) & (frequency < hi)].sum(axis=0)
        fractions[f"{lo}_{hi}_hz"] = [float(energy[e] / total[e]) if total[e] else None for e in range(2)]
    audible_total = spectrum[(frequency >= 20) & (frequency < 20000)].sum(axis=0)
    audible_fractions = {}
    for lo, hi in [(20, 250), (250, 500), (500, 2000), (2000, 8000), (8000, 20000)]:
        energy = spectrum[(frequency >= lo) & (frequency < hi)].sum(axis=0)
        audible_fractions[f"{lo}_{hi}_hz"] = [float(energy[e] / audible_total[e]) if audible_total[e] else None for e in range(2)]
    sub20 = spectrum[frequency < 20].sum(axis=0)
    centered = samples - samples.mean(axis=0)
    den = float(np.sqrt(np.sum(centered[:, 0] ** 2) * np.sum(centered[:, 1] ** 2)))
    correlation = float(np.sum(centered[:, 0] * centered[:, 1]) / den) if den else None
    return {
        "frames": n,
        "sample_rate_hz": rate,
        "channels": 2,
        "duration_s": n / rate,
        "rms_dbfs": [dbfs(float(v)) for v in rms],
        "peak_dbfs": [dbfs(float(v)) for v in peaks],
        "left_minus_right_db": dbfs(float(rms[0] / rms[1])) if rms[0] > 0 and rms[1] > 0 else None,
        "channel_correlation": correlation,
        "band_energy_fractions": fractions,
        "audible_band_energy_fractions": audible_fractions,
        "sub_20hz_fraction_of_total_power": [float(sub20[e] / total[e]) if total[e] else None for e in range(2)],
        "dc_sample_mean": samples.mean(axis=0).tolist(),
        "samples_above_full_scale": int(np.count_nonzero(np.abs(samples) > 1)),
        "silent": bool(np.max(peaks) == 0),
        "decoded_float64_sha256": hashlib.sha256(samples.astype("<f8").tobytes()).hexdigest(),
        "meaning": "Unweighted digital descriptors. No listening or device-equivalence conclusion.",
    }
