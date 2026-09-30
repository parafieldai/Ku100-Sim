"""Microphone-domain statistical waveform synthesis. NOT contact mechanics.

Fits stationary, multi-resolution envelope statistics, never a waveform or event
schedule. Rendering optimizes a fresh waveform against those statistics. This is
an original small implementation inspired by auditory-texture research, not a
reproduction of an auditory model or an assertion of perceptual equivalence.
PyTorch is needed only for this optional offline source experiment.
"""
from __future__ import annotations
import hashlib
import json
import math
import lzma
import io
import struct
import copy
from pathlib import Path
import numpy as np
from scipy import signal

RATE = 48000
FFTS = (256, 1024, 4096)
LAGS = (0, 1, 2, 4, 8, 16)
SCHEMA = 'correlated-texture-source/1'


def _torch():
    import torch
    torch.set_num_threads(2)
    return torch


def _finite(x, lo, hi):
    try:
        return type(x) in (int, float) and math.isfinite(x) and lo <= x <= hi
    except OverflowError:
        return False


def bank(nfft):
    """Log-spaced triangular spectral analysis, not calibrated cochlear filters."""
    f = np.fft.rfftfreq(nfft, 1/RATE)
    edges = np.r_[0., np.geomspace(40., 22000., 22), RATE/2]
    rows = []
    for i in range(1, len(edges)-1):
        w = np.maximum(0., np.minimum((f-edges[i-1])/(edges[i]-edges[i-1]),
                                      (edges[i+1]-f)/(edges[i+1]-edges[i])))
        if w.sum() > 1e-10:
            rows.append(w/w.sum())
    return np.array(rows, dtype=np.float32)


class Analyzer:
    def __init__(self):
        t = _torch()
        self.t = t
        self.banks = [(n, t.hann_window(n), t.tensor(bank(n))) for n in FFTS]

    def raw(self, x):
        rows = []
        for n, window, weights in self.banks:
            spectrum = self.t.stft(x, n_fft=n, hop_length=n//4,
                window=window, return_complex=True)
            # Exclude boundary padding: never learn a splice between ranges.
            power = spectrum.abs().square()[:, 2:-2]
            envelope = (weights @ power + 1e-10).sqrt()
            rows.append((power, envelope))
        return rows

    def descriptor(self, segments, norm):
        t = self.t
        output = []
        for k in range(len(FFTS)):
            powers = t.cat([r[k][0] for r in segments], -1)
            es = [(r[k][1]/norm[k]).clamp_min(1e-7).sqrt() for r in segments]
            z = t.cat(es, -1)
            mean = z.mean(-1, keepdim=True)
            std = z.std(-1, keepdim=True, unbiased=False).clamp_min(.015)
            center = (z-mean)/std
            desc = {
                'log_power': powers.mean(-1).clamp_min(1e-8).log(),
                'mean': mean, 'std': std,
                'skew': center.pow(3).mean(-1, keepdim=True),
                'kurtosis': center.pow(4).mean(-1, keepdim=True),
            }
            # Preserve dependencies between bands and across time; no original
            # phase/timeline is stored, and lags never cross a training boundary.
            for lag in LAGS:
                count = sum(e.shape[-1]-lag for e in es)
                desc['lag_'+str(lag)] = sum(
                    e[:,lag:] @ (e[:,:-lag].T if lag else e.T)
                    for e in es)/count
            delta = t.cat([e[:,1:]-e[:,:-1] for e in es], -1)
            desc['attack'] = delta.clamp_min(0).square().mean(-1)
            desc['release'] = (-delta).clamp_min(0).square().mean(-1)
            output.append(desc)
        return output


def _as_list(x):
    return np.asarray(x, dtype=np.float64).round(7).tolist()


def fit(samples, provenance):
    """samples: separately supplied mono ranges, resampled to 48 kHz by caller."""
    t = _torch()
    if not samples or any(np.asarray(x).ndim != 1 or len(x) < RATE for x in samples):
        raise ValueError('Need separate mono ranges >= 1 s')
    if any(not np.isfinite(x).all() for x in samples):
        raise ValueError('Nonfinite fitting waveform')
    # One global training scalar; never divide every quiet event by its own RMS.
    rms = math.sqrt(sum(float(np.sum(x*x)) for x in samples)/sum(map(len,samples)))
    if not 1e-7 < rms < 10:
        raise ValueError('Degenerate fitting level')
    analyzer = Analyzer()
    with t.no_grad():
        wave = [t.tensor(x/rms, dtype=t.float32) for x in samples]
        raw = [analyzer.raw(x) for x in wave]
        norm = [t.cat([s[k][1] for s in raw], -1).mean(-1, keepdim=True).clamp_min(1e-4)
                for k in range(len(FFTS))]
        desc = analyzer.descriptor(raw, norm)
        moments = [sum(x.abs().pow(p).sum() for x in wave)/sum(x.numel() for x in wave)
                   for p in [1,3,4]]
    model = {'schema':SCHEMA,'rate':RATE,'physical_model':False,
             'runtime_reference_audio':False,'phase_or_timeline_stored':False,
             'normalizers':[_as_list(s) for s in norm],
             'statistics':[{k:_as_list(v) for k,v in row.items()} for row in desc],
             'absolute_moments':[_as_list(v) for v in moments],
             'training_rms':rms,'training_frames':sum(map(len,samples)),
             'provenance':provenance,
             'limitations':['Stationary acoustic statistics, not identified tongue/saliva mechanics.',
                            'No source separation or calibrated device transfer.',
                            'Matching fitted statistics is not a perceptual acceptance result.']}
    validate(model)
    return model


def validate(model):
    if not isinstance(model,dict) or model.get('schema') != SCHEMA or model.get('rate') != RATE:
        raise ValueError('Wrong texture model schema or rate')
    for k in ['physical_model','runtime_reference_audio','phase_or_timeline_stored']:
        if model.get(k) is not False:
            raise ValueError('Texture model must retain source/provenance boundaries')
    if not _finite(model.get('training_rms'),1e-7,10):
        raise ValueError('Invalid training level')
    if len(model.get('normalizers',[]))!=3 or len(model.get('statistics',[]))!=3:
        raise ValueError('Invalid analysis scales')
    for k,n in enumerate(FFTS):
        bands = len(bank(n))
        normalizer = np.asarray(model['normalizers'][k],dtype=float)
        if normalizer.shape != (bands,1) or not np.isfinite(normalizer).all() or np.any(normalizer<1e-4):
            raise ValueError('Invalid normalizer')
        shapes = {'log_power':(n//2+1,), 'mean':(bands,1), 'std':(bands,1),
                  'skew':(bands,1),'kurtosis':(bands,1),'attack':(bands,), 'release':(bands,)}
        shapes.update({'lag_'+str(l):(bands,bands) for l in LAGS})
        if set(shapes)!=set(model['statistics'][k]):
            raise ValueError('Missing/extra statistic')
        for key,shape in shapes.items():
            values=np.asarray(model['statistics'][k][key],dtype=float)
            if values.shape!=shape or not np.isfinite(values).all() or np.max(abs(values))>1e6:
                raise ValueError('Invalid statistic: '+key)
        if any(np.any(np.asarray(model['statistics'][k][key])<=0) for key in ['mean','std','kurtosis']):
            raise ValueError('Invalid positive moments')
        if np.max(abs(np.array(model['statistics'][k]['log_power'])))>50:
            raise ValueError('Invalid log power')
    a=np.asarray(model.get('absolute_moments'),dtype=float)
    if a.shape!=(3,) or not np.isfinite(a).all() or np.any(a<=0):
        raise ValueError('Invalid waveform moments')



def pack(model):
    """Bounded float16 statistics container; no waveform/phase/timeline payload.

    The small parameter quantization is recorded, not called lossless audio.
    Inference and optimization still use float32; microphone output is float32.
    """
    validate(model)
    meta=copy.deepcopy(model);arrays=[]
    for value in meta.pop('normalizers'):
        arrays.append(np.asarray(value,dtype='<f2').ravel())
    shapes=[]
    for row in meta.pop('statistics'):
        fields=[]
        for key in sorted(row):
            a=np.asarray(row[key]);fields.append([key,list(a.shape)])
            arrays.append(a.astype('<f2').ravel())
        shapes.append(fields)
    arrays.append(np.asarray(meta.pop('absolute_moments'),dtype='<f2'))
    blob=np.concatenate(arrays)
    if not np.isfinite(blob).all():raise ValueError('Target statistic exceeds float16 range')
    meta['parameter_storage']='float16; optimization uses float32'
    header=json.dumps({'model':meta,'shapes':shapes},separators=(',',':'),allow_nan=False).encode()
    return lzma.compress(b'KTX1'+struct.pack('<I',len(header))+header+blob.tobytes())


def unpack(raw):
    if raw[:4]!=b'KTX1' or len(raw)<8:raise ValueError('Invalid compact model')
    size=struct.unpack('<I',raw[4:8])[0]
    if not 0<size<16000 or 8+size>len(raw):raise ValueError('Invalid compact header')
    head=json.loads(raw[8:8+size]);model=head['model'];offset=8+size
    def read(shape):
        nonlocal offset
        if not isinstance(shape,list) or any(type(x) is not int or not 0<x<3000 for x in shape):raise ValueError('Invalid compact shape')
        count=math.prod(shape)
        if count>5000 or offset+2*count>len(raw):raise ValueError('Truncated compact data')
        a=np.frombuffer(raw,dtype='<f2',count=count,offset=offset).astype(np.float32).reshape(shape);offset+=2*count
        if not np.isfinite(a).all():raise ValueError('Nonfinite compact statistic')
        return a.tolist()
    model['normalizers']=[read([len(bank(n)),1]) for n in FFTS]
    shapes=head['shapes']
    if not isinstance(shapes,list) or len(shapes)!=3:raise ValueError('Invalid compact scales')
    model['statistics']=[]
    for row in shapes:
        if not isinstance(row,list) or len(row)!=13:raise ValueError('Invalid compact fields')
        fields={}
        for key,shape in row:
            if key in fields:raise ValueError('Duplicate compact field')
            fields[key]=read(shape)
        model['statistics'].append(fields)
    model['absolute_moments']=read([3])
    if offset!=len(raw):raise ValueError('Unexpected trailing compact data')
    validate(model);return model


def load(path):
    path=Path(path)
    if path.stat().st_size>500000:
        raise ValueError('Texture model exceeds 500 kB')
    def pairs(rows):
        d={}
        for k,v in rows:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    raw=path.read_bytes()
    if path.suffix=='.xz':
        with lzma.LZMAFile(io.BytesIO(raw)) as f:raw=f.read(500001)
        if len(raw)>500000:raise ValueError('Expanded texture model exceeds 500 kB')
    if raw[:4]==b'KTX1':return unpack(raw)
    m=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    validate(m)
    return m


def loss_terms(current, targets, waveform, moments):
    t = _torch()
    losses = {}
    for i,(row,goal) in enumerate(zip(current,targets)):
        for key,want in goal.items():
            have=row[key]
            if key=='log_power':
                error=(have-want).square().mean()*.12
            elif key in ['skew','kurtosis']:
                error=((have-want)/(want.abs()+1)).square().mean()*.25
            elif key in ['attack','release']:
                error=((have+1e-5).log()-(want+1e-5).log()).square().mean()*.12
            else:
                error=(have-want).square().mean()
            losses[f'{i}:{key}']=error
    for i,p in enumerate([1,3,4]):
        value=waveform.abs().pow(p).mean().clamp_min(1e-6)
        losses['sample_moment_'+str(p)]=(value.log()-moments[i].log()).square()*.15
    losses['dc']=waveform.mean().square()*10
    return losses


def synthesize(model, *, seconds=6., seed=307, iterations=800, phase_only=False, boundary_fade=True):
    """Generate fresh waveform via optimization of aggregate statistics only.

    It is offline, noncausal, acoustic synthesis, not a neural decoder, a new
    measured performance, or an action-controlled physical simulation.
    """
    validate(model)
    if not _finite(seconds,1,12) or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('Invalid duration or seed')
    if type(iterations) is not int or not 0<=iterations<=2000:
        raise ValueError('Iterations must be an integer in [0,2000]')
    if type(phase_only) is not bool or type(boundary_fade) is not bool:raise ValueError('Invalid rendering flag')
    t=_torch(); analyzer=Analyzer()
    norm=[t.tensor(a,dtype=t.float32) for a in model['normalizers']]
    target=[{k:t.tensor(v,dtype=t.float32) for k,v in row.items()} for row in model['statistics']]
    moments=t.tensor(model['absolute_moments'],dtype=t.float32)
    n=round(seconds*RATE);rng=np.random.default_rng(seed)
    # Initialization has the training power shape, but random fresh phase.
    freq=np.fft.rfftfreq(n,1/RATE)
    ps=np.exp(np.interp(freq,np.fft.rfftfreq(FFTS[-1],1/RATE),
                       model['statistics'][-1]['log_power']))
    white=rng.standard_normal(n)
    initial=np.fft.irfft(np.fft.rfft(white)*np.sqrt(ps),n=n)
    initial-=initial.mean();initial/=np.sqrt(np.mean(initial**2))
    color=t.tensor(np.sqrt(ps)/np.sqrt(np.mean(np.fft.irfft(np.fft.rfft(white)*np.sqrt(ps),n=n)**2)),dtype=t.float32)
    innovation=t.tensor(white,dtype=t.float32,requires_grad=True)
    initial_fft=np.fft.rfft(initial)
    magnitude=t.tensor(abs(initial_fft),dtype=t.float32)
    phase=t.tensor(np.angle(initial_fft),dtype=t.float32,requires_grad=True)
    optimizer=t.optim.Adam([phase if phase_only else innovation],lr=.12 if phase_only else .045)
    history=[]
    best=None;best_loss=float('inf')
    # Preserve the best measured iterate, rather than assuming more steps help.
    for i in range(iterations+1):
        optimizer.zero_grad()
        waveform=(t.fft.irfft(t.polar(magnitude,phase),n=n) if phase_only else
                  t.fft.irfft(t.fft.rfft(innovation)*color,n=n))
        current=analyzer.descriptor([analyzer.raw(waveform)],norm)
        terms=loss_terms(current,target,waveform,moments)
        loss=sum(terms.values())
        value=float(loss.detach())
        if not math.isfinite(value):raise ValueError('Nonfinite optimizer')
        if value<best_loss:
            best_loss=value;best=waveform.detach().numpy().copy()
        if i%50==0 or i==iterations:
            history.append({'iteration':i,'loss':value})
        if i==iterations:break
        loss.backward()
        optimizer.param_groups[0]['lr']=(.12 if phase_only else .045)*(.15+.85*(1+math.cos(math.pi*i/max(iterations,1)))/2)
        optimizer.step()
    # No compression, per-band EQ, or sample replay is applied to the optimum.
    # A fixed 10 ms fade only avoids an abrupt file boundary.
    y=best.astype(float);fade=min(round(.01*RATE),len(y)//2)
    window=.5-.5*np.cos(np.linspace(0,np.pi,fade))
    if boundary_fade:
        y[:fade]*=window;y[-fade:]*=window[::-1]
    y*=.025 # one declared fixed digital scale, not pressure calibration
    if not np.isfinite(y).all() or abs(y).max()>=1:
        raise ValueError('Nonfinite or over-full-scale output; refusing to limit')
    info={'schema':'texture-render/1','physical_model':False,'seed':seed,'seconds':seconds,
        'iterations':iterations,'optimizer':'Adam, fixed-magnitude phases' if phase_only else 'Adam, whitened waveform coordinates',
        'fixed_spectrum_before_boundary_fade':phase_only,
        'history':history,'best_objective':best_loss,'fixed_digital_scale':.025,
        'boundary_fade_s':.01 if boundary_fade else 0,'reference_reads_at_render':0,'units':'uncalibrated digital audio',
        'model_sha256':hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'target_accepted':False,'human_listening':'not performed'}
    return y,info


def frozen_stereo_transfer(old_model, source):
    """One fixed inter-ear shaper inherited from the previous burst fit.

    Apply IDENTICALLY to new/old/control sources for this source-only comparison.
    This average minimum-phase path is an acoustic assumption, not an HRTF.
    No spatial parameter is optimized by the new texture model.
    """
    from .burst_source import validate_model, KNOTS
    parameters=validate_model(old_model);near=old_model['near_channel'];far=1-near
    logratio=(parameters[:,far]-parameters[:,near]).mean(0)
    fft=2048
    cep=np.fft.irfft(np.interp(np.fft.rfftfreq(fft,1/RATE),KNOTS,logratio),n=fft)
    causal=np.zeros(fft);causal[0]=cep[0];causal[1:fft//2]=2*cep[1:fft//2];causal[fft//2]=cep[fft//2]
    h=np.fft.irfft(np.exp(np.fft.rfft(causal)),n=fft)[:1024]
    h[-128:]*=.5*(1+np.cos(np.linspace(0,np.pi,128)))
    out=np.zeros((len(source)+len(h)-1,2));out[:len(source),near]=source
    out[:,far]=signal.fftconvolve(source,h)
    return out,{'method':'Fixed minimum-phase inter-ear log-magnitude ratio from previous burst model',
       'near_channel':near,'shared_across_all_sources':True,'new_spatial_fit':False,
       'coefficients_sha256':hashlib.sha256(h.astype('<f8').tobytes()).hexdigest(),
       'physical_transfer_validated':False,'tail_frames':len(h)-1}
