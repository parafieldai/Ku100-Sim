#!/usr/bin/env python3
"""Compare numerical reference-audit summaries with fresh native examples.

This offline diagnostic reads an existing user audit, never a performance at
render time. It cannot identify hardware or establish perceptual equivalence.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
BANDS = [(0, 80), (80, 250), (250, 1000), (1000, 4000), (4000, 10000), (10000, 30000)]


def band_summary(samples, rate):
    # Analysis-only resampling gives the same window duration and frequency grid
    # as the recovered 44.1 kHz audit. The native WAV is never modified.
    divisor = math.gcd(rate, 44100)
    x = signal.resample_poly(samples, 44100 // divisor, rate // divisor, axis=0)
    segments = max(1, math.ceil(max(0, len(x) - 8192) / 4096)) + 1
    padded = np.pad(x, ((0, (segments - 1) * 4096 + 8192 - len(x)), (0, 0)))
    frequencies, power = signal.welch(padded, fs=44100, window='hann', nperseg=8192,
                                      noverlap=4096, detrend='constant', scaling='density', axis=0)
    total = power.sum(axis=0)
    rows = []
    for low, high in BANDS:
        part = power[(frequencies >= low) & (frequencies < high)].sum(axis=0)
        rows.append({'low_hz': low, 'high_hz': min(high, 22050),
                     **{ear + '_power_percent': float(part[i] / total[i] * 100) if total[i] else None
                        for i, ear in enumerate(['L', 'R'])}})
    return rows


def compare(audit_path, examples_dir):
    audit_bytes = audit_path.read_bytes()
    audit = json.loads(audit_bytes)
    references = []
    for clip in audit['clips']:
        references.append({'chapter': clip['chapter'], 'filename_label': clip['stereo']['filename_label'],
                           'file_sha256': clip['sha256_file'], 'pcm_sha256': clip['sha256_pcm'],
                           'duration_s': clip['duration_s'], 'rate_hz': clip['sample_rate_hz'],
                           'rms_dbfs': [clip['per_channel'][ear]['rms_dbfs'] for ear in ['L', 'R']],
                           'left_minus_right_db': clip['stereo']['whole_file_l_minus_r_rms_db'],
                           'correlation': clip['stereo']['zero_lag_sample_pearson_r'],
                           'bands': [{key: row[key] for key in ['low_hz', 'high_hz', 'L_power_percent', 'R_power_percent']}
                                     for row in clip['spectra']['bands']]})
    examples = []
    for path in sorted(examples_dir.glob('*.ku100.json')):
        bundle = json.loads(path.read_text())
        raw = base64.b64decode(bundle['audio']['base64'], validate=True)
        if hashlib.sha256(raw).hexdigest() != bundle['audio']['sha256']:
            raise ValueError('Native bundle has a corrupt audio identity')
        rate, samples = wavfile.read(BytesIO(raw))
        if samples.ndim != 2 or samples.shape[1] != 2 or not np.isfinite(samples).all():
            raise ValueError('A finite stereo native WAV is required')
        samples = samples.astype(np.float64)
        rms = np.sqrt(np.mean(samples ** 2, axis=0))
        levels = [float(20 * np.log10(x)) if x else None for x in rms]
        examples.append({'example': path.stem.replace('.ku100', ''), 'mode': bundle['scene']['receiver']['mode'],
                         'duration_s': len(samples) / rate, 'rate_hz': rate, 'audio_sha256': bundle['audio']['sha256'],
                         'native_source_digest': bundle['provenance']['native_source_digest'], 'rms_dbfs': levels,
                         'left_minus_right_db': levels[0] - levels[1] if all(x is not None for x in levels) else None,
                         'correlation': float(np.corrcoef(samples.T)[0, 1]) if np.all(np.std(samples, axis=0) > 0) else None,
                         'bands': band_summary(samples, rate)})
    return {'version': 1, 'reference_audit_sha256': hashlib.sha256(audit_bytes).hexdigest(),
            'reference_total_duration_s': audit['total_duration_s'],
            'reference_source_provenance': audit['source_provenance'],
            'method': 'Whole-file RMS and mean-removed zero-lag sample correlation. Spectra use Hann8192/hop4096 at44.1kHz, constant detrend, mean PSD, final partial window zero-padded. Native data are resampled only for analysis.',
            'limits': ['Reference device, original source, calibration and gain are unverified.',
                       'Reference performances and simulations have different actions, durations and force histories.',
                       'No fit, waveform alignment, per-ear gain or runtime replay is used.',
                       'These descriptive differences are not a perceptual or physical-equivalence score.'],
            'references': references, 'examples': examples}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-audit', type=Path, required=True)
    parser.add_argument('--examples', type=Path, default=ROOT / 'web/examples')
    parser.add_argument('--out', type=Path, default=ROOT / 'validation/reference-comparison.json')
    args = parser.parse_args()
    result = compare(args.reference_audit, args.examples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'references': len(result['references']), 'examples': len(result['examples']), 'out': str(args.out)}))
