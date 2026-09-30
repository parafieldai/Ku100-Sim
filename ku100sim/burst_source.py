"""Empirical microphone-domain burst source, NOT a contact-physics solver.

A compact phase-dependent spectral envelope is fitted to pooled detected events.
At render time a fresh renewal pulse sequence excites minimum-phase FIRs. No
recorded samples, event timelines, force labels, HRIRs or neural weights are read.
This is an acoustic baseline for falsification/listening, not a realism claim.
"""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.fft import rfft, irfft

SR = 48000
PHASES = 16
NFFT = 2048
TAPS = 1024
KNOTS = np.concatenate(([0.0], np.geomspace(24.0, 20000.0, 64), [24000.0]))


def finite_number(value, lo, hi):
    try:
        return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi
    except OverflowError:
        return False


def validate_model(model: dict) -> np.ndarray:
    if not isinstance(model, dict) or model.get('schema') != 'empirical-burst-source/1':
        raise ValueError('Expected empirical-burst-source/1')
    if model.get('physical_model') is not False or model.get('sample_rate_hz') != SR:
        raise ValueError('This source must not be represented as calibrated physics')
    if model.get('near_channel') not in [0, 1] or type(model['near_channel']) is not int:
        raise ValueError('Invalid channel identity')
    for key, lo, hi in [('duration_median_s', .04, .30), ('duration_log_std', 0, 2),
                        ('rms_median', .000001, 2), ('rms_log_std', 0, 2),
                        ('detected_event_rate_hz', .01, 20)]:
        if not finite_number(model.get(key), lo, hi):
            raise ValueError('Invalid model parameter: '+key)
    a = np.asarray(model.get('log_magnitude'), dtype=np.float64)
    if a.shape != (PHASES, 2, len(KNOTS)) or not np.isfinite(a).all() or np.max(abs(a)) > 40:
        raise ValueError('Invalid pooled spectral parameters')
    return a


def load_model(path: Path) -> dict:
    if path.stat().st_size > 150000:
        raise ValueError('Model exceeds 150,000 bytes')
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj: raise ValueError('Duplicate model field')
            obj[k] = v
        return obj
    m = json.loads(path.read_text(), object_pairs_hook=pairs,
                   parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite model')))
    validate_model(m)
    return m


def event_candidates(x: np.ndarray, sr: int, near: int) -> list[tuple[int, int, int]]:
    """Acoustic candidates only. A peak is not proof of peel, suction or a bubble."""
    if type(sr) is not int or not 8000 <= sr <= 192000 or type(near) is not int or near not in (0,1):
        raise ValueError('Invalid sample rate or channel')
    if x.ndim != 2 or x.shape[1] != 2 or not np.isfinite(x).all() or len(x) < sr:
        raise ValueError('Need finite stereo audio of at least one second')
    y = signal.sosfilt(signal.butter(3, 100, fs=sr, btype='high', output='sos'), x[:, near])
    hop = round(.004 * sr)
    y = y[:len(y)//hop*hop]
    e = np.sqrt(np.mean(y.reshape(-1, hop)**2, axis=1))
    e = signal.convolve(e, [.25, .5, .25], mode='same')
    peaks, _ = signal.find_peaks(e, prominence=max(np.percentile(e, 75)*.6, 1e-5), distance=21)
    result = []
    for peak in peaks:
        a = b = int(peak)
        threshold = e[peak]*.15
        while a > 0 and peak-a < 30 and threshold < e[a-1] < e[a]: a -= 1
        while b < len(e)-1 and b-peak < 65 and e[b+1] > threshold: b += 1
        start, end = max(0, a-1)*hop, min(len(x), (b+1)*hop)
        if .04 <= (end-start)/sr <= .30:
            result.append((start, end, int(peak)*hop))
    return result


def filter_bank(model: dict) -> np.ndarray:
    a = validate_model(model)
    frequencies = np.fft.rfftfreq(NFFT, 1/SR)
    bank = np.empty((PHASES, 2, TAPS))
    for phase in range(PHASES):
        for c in range(2):
            logmag = np.interp(frequencies, KNOTS, a[phase,c])
            cep = irfft(logmag, n=NFFT)
            lift = np.zeros(NFFT)
            lift[0], lift[NFFT//2] = cep[0], cep[NFFT//2]
            lift[1:NFFT//2] = 2*cep[1:NFFT//2]
            bank[phase,c] = irfft(np.exp(rfft(lift)), n=NFFT)[:TAPS]
            bank[phase,c] *= np.r_[np.ones(TAPS-128), .5*(1+np.cos(np.linspace(0,np.pi,128)))]
    # Exactly ONE shared scale for all phases and channels, not ear normalization.
    scale = np.sqrt(np.mean(np.sum(bank[:,model['near_channel']]**2, axis=1)))
    if not math.isfinite(scale) or scale < 1e-10: raise ValueError('Degenerate spectral bank')
    return bank/scale


def synthesize(model: dict, *, seconds=6.0, seed=90291, rate_scale=1.0,
               gate_end=None, continuous_ablation=False):
    """Fresh acoustic events. Controls are not N, m/s, saliva quantity or wetness."""
    if not finite_number(seconds, 1, 30) or not finite_number(rate_scale, .5, 2):
        raise ValueError('Duration must be 1–30 s and acoustic rate scale 0.5–2')
    if type(seed) is not int or not 0 <= seed <= 2**32-1: raise ValueError('Invalid seed')
    if type(continuous_ablation) is not bool: raise ValueError('Invalid ablation flag')
    if gate_end is None: gate_end = seconds-.3
    if not finite_number(gate_end, 0, seconds): raise ValueError('Invalid gate end')
    bank = filter_bank(model)
    near = model['near_channel']
    rng = np.random.default_rng(seed)
    n = round(seconds*SR)
    output = np.zeros((n,2), dtype=np.float64)
    events = []
    time = .2
    while time < gate_end-.04:
        duration = float(np.clip(rng.lognormal(np.log(model['duration_median_s']),
                                              model['duration_log_std']*.7), .04, .30))
        duration = min(duration, gate_end-time)
        count = max(2, round(duration*SR))
        excitation = np.zeros(count)
        at = 0
        # Authored pulse-density hypothesis, not inferred force or measured bubbles.
        while at < count:
            excitation[at] = rng.choice([-1.,1.])*min(rng.lognormal(0,.6), 8.)
            at += max(1, round(rng.exponential(SR/1500)))
        excitation[0] += 3*rng.choice([-1.,1.])
        rendered = np.zeros((count+TAPS-1,2))
        for phase in range(PHASES):
            center = phase*(count-1)/(PHASES-1)
            weight = np.maximum(0, 1-abs(np.arange(count)-center)/((count-1)/(PHASES-1)))
            for c in range(2): rendered[:,c] += signal.fftconvolve(excitation*weight, bank[phase,c])
        rms = float(np.sqrt(np.mean(rendered[:,near]**2)))
        amplitude = float(np.clip(rng.lognormal(np.log(model['rms_median']),
                                   min(.65,model['rms_log_std'])), .00001,.20))
        rendered *= amplitude/max(rms,1e-12)
        start = round(time*SR)
        stop = min(n,start+len(rendered))
        output[start:stop] += rendered[:stop-start]
        events.append({'onset_s':time, 'excitation_duration_s':duration,
                       'acoustic_rms_request':amplitude})
        time += max(duration*.75, float(rng.gamma(5,1/(5*model['detected_event_rate_hz']*rate_scale))))
    if continuous_ablation and gate_end > .2:
        # Negative control: erase event-conditioned timbral evolution and grouping.
        output.fill(0)
        count = round((gate_end-.2)*SR)
        pulse = np.zeros(count)
        index=0
        while index<count:
            pulse[index]=rng.choice([-1.,1.])*min(rng.lognormal(0,.6),8.)
            index+=max(1,round(rng.exponential(SR/1500)))
        for c in range(2):
            y=signal.fftconvolve(pulse,bank.mean(0)[c]);stop=min(n,round(.2*SR)+len(y))
            output[round(.2*SR):stop,c]=y[:stop-round(.2*SR)]
        scale=np.sqrt(np.mean(output[:,near]**2))
        output *= model['rms_median']/max(scale,1e-12)
        events=[]
    # Fixed shared digital headroom, never a limiter or independently fitted ear gain.
    output *= .1
    if not np.isfinite(output).all(): raise ValueError('Nonfinite synthesis')
    info={'schema':'empirical-burst-render/1','physical_model':False,
          'mechanism_identified':False,'perceptual_acceptance':'not_assessed',
          'sample_rate_hz':SR,'seconds':seconds,'seed':seed,'rate_scale':rate_scale,
          'gate_end_s':gate_end,'continuous_ablation':continuous_ablation,
          'shared_digital_gain':.1,'near_channel':near,'events':events,
          'model_sha256':hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
          'runtime_reference_audio_reads':0,'units':'digital amplitude, not pascals',
          'note':'Pooled recording-domain spectral envelopes and fresh filtered impulses; not simulated saliva or KU100 geometry.'}
    return output,info


def wav_bytes(x: np.ndarray, rate: int = SR) -> bytes:
    if (type(rate) is not int or not 8000 <= rate <= 192000 or x.ndim != 2 or x.shape[1]!=2
            or not 1 <= len(x) <= rate*31 or not np.isfinite(x).all() or np.max(abs(x))>np.finfo(np.float32).max):
        raise ValueError('Invalid stereo waveform')
    b=x.astype('<f4').tobytes()
    return b'RIFF'+struct.pack('<I',36+len(b))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,3,2,rate,rate*8,8,32)+b'data'+struct.pack('<I',len(b))+b
