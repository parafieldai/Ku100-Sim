"""Data-assisted, stable modal object response. Not a full geometry/force solver.

Damped modes are identified from corrected microphone measurements. Resonance
frequencies, damping and two output residues per mode are retained, not clips.
The residues include unseparated source/radiation/capture effects at the fitted
measurement position. Output and input impulse are relative units, never Pa/N.
"""
from __future__ import annotations
import math
import numpy as np
from scipy import signal, optimize

RATE = 48000
SCHEMA = 'measured-modal-object/1'

def validate(model):
    if not isinstance(model, dict) or model.get('schema') != SCHEMA:
        raise ValueError('Unsupported modal-object model')
    if model.get('sample_rate') != RATE or model.get('calibrated_force_to_pressure') is not False:
        raise ValueError('Uncalibrated 48 kHz model required')
    forbidden={'waveform','reference_pcm','residual_samples','samples'}
    if forbidden & model.keys(): raise ValueError('Waveform payload is forbidden')
    a = np.asarray(model.get('modes'), dtype=float)
    if a.ndim != 2 or a.shape[1] != 4 or not 1 <= len(a) <= 64 or not np.isfinite(a).all():
        raise ValueError('Expected 1–64 finite [Hz, decay/s, cos residue, sin residue] modes')
    if np.any((a[:, 0] < 80) | (a[:, 0] > 18000) | (a[:, 1] < .1) | (a[:, 1] > 4000)) or np.max(abs(a[:, 2:])) > 20:
        raise ValueError('Modal parameters out of range')
    return a

def impulse_response(model, seconds=2., *, damping_scale=1.):
    modes = validate(model)
    if type(seconds) not in (float, int) or not math.isfinite(seconds) or not .01 <= seconds <= 12:
        raise ValueError('Duration must be 0.01–12 seconds')
    if type(damping_scale) not in (float, int) or not math.isfinite(damping_scale) or not .5 <= damping_scale <= 8:
        raise ValueError('Invalid decay multiplier')
    t = np.arange(round(seconds * RATE)) / RATE
    y = np.zeros(len(t))
    for f, decay, c, s in modes:
        y += np.exp(-decay * damping_scale * t) * (c * np.cos(2*np.pi*f*t) + s*np.sin(2*np.pi*f*t))
    return y

def render(model, events, seconds=6., *, damping_scale=1.):
    """Fresh impulse excitation through a stable IIR response; no file reads.

    Event = (time_s, relative_impulse, pulse_width_s). Pulse is half-sine with
    unit discrete area, scaled by relative impulse. Changing width is an
    excitation experiment, not calibrated material/hammer-force prediction.
    """
    modes = validate(model)
    if type(seconds) not in (float, int) or not math.isfinite(seconds) or not .1 <= seconds <= 30:
        raise ValueError('Duration must be 0.1–30 s')
    if type(damping_scale) not in (float, int) or not math.isfinite(damping_scale) or not .5 <= damping_scale <= 8:
        raise ValueError('Invalid damping scale')
    if not isinstance(events, (list, tuple)) or len(events) > 100:
        raise ValueError('Bounded event list required')
    x = np.zeros(round(seconds*RATE))
    for event in events:
        if not isinstance(event, (list, tuple)) or len(event) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in event):
            raise ValueError('Invalid excitation event')
        at, strength, width = event
        if not 0 <= at < seconds or not 0 <= strength <= 2 or not 0 <= width <= .004:
            raise ValueError('Event out of bounds')
        n = max(1, round(width*RATE))
        pulse = np.sin(np.pi*(np.arange(n)+.5)/n); pulse *= strength / pulse.sum()
        start = round(at*RATE)
        if start+n > len(x): raise ValueError('Event crosses output boundary')
        x[start:start+n] += pulse
    y = np.zeros(len(x))
    for f, decay, c, s in modes:
        r = math.exp(-decay*damping_scale/RATE); theta=2*math.pi*f/RATE
        y += signal.lfilter([c, r*(s*math.sin(theta)-c*math.cos(theta))], [1, -2*r*math.cos(theta), r*r], x)
    if not np.isfinite(y).all(): raise ValueError('Nonfinite synthesis')
    return y

def crop_measurement(x, seconds=1.5):
    """Fixed 0.1-ms RMS onset rule; source-local onset, never candidate-fitted delay."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or len(x) < RATE*2 or not np.isfinite(x).all():
        raise ValueError('Need >= 2 s finite mono measurement')
    x = signal.sosfilt(signal.butter(2, 80, btype='high', fs=RATE, output='sos'), x)
    envelope = np.sqrt(signal.convolve(x[:RATE//4]**2, np.ones(5)/5, mode='same'))
    if envelope.max()<1e-10: raise ValueError('Silent measurement')
    onset = max(0, int(np.flatnonzero(envelope > .08*envelope.max())[0])-2)
    y = x[onset:onset+round(seconds*RATE)].copy()
    scale = float(np.max(abs(y)))
    if scale < 1e-10: raise ValueError('Silent measurement')
    return y/scale, {'onset_sample':onset, 'fixed_highpass_hz':80, 'normalization_peak':scale, 'duration_s':seconds}

def fit_modes(samples, max_modes=24):
    """Greedy variable-projection damped-sinusoid fit, then joint residue solve.

    Only the supplied training measurement enters this fitter. Not ESPRIT,
    not estimated Young's modulus, and not phase-free statistical texture.
    """
    if type(max_modes) is not int or not 1<=max_modes<=64: raise ValueError('Invalid mode count')
    y, prep = crop_measurement(samples)
    t = np.arange(len(y))/RATE
    residual = y.copy(); rows=[]; history=[]
    nfft=2**math.ceil(math.log2(len(y)*2)); freq=np.fft.rfftfreq(nfft,1/RATE)
    weight=np.exp(-t/.45)
    def basis(f,d):
        e=np.exp(-d*t);a=2*np.pi*f*t
        return np.column_stack([e*np.cos(a),e*np.sin(a)])
    for it in range(max_modes):
        spectrum=abs(np.fft.rfft(residual*weight,nfft))
        spectrum[(freq<100)|(freq>16000)]=0
        peaks,_=signal.find_peaks(spectrum, distance=max(1,int(12*nfft/RATE)))
        if not len(peaks): break
        ix=peaks[np.argmax(spectrum[peaks])];f0=float(freq[ix])
        def objective(params, return_parts=False):
            f,d=params[0],math.exp(params[1]);B=basis(f,d)
            gram=B.T@B
            coef=np.linalg.solve(gram+np.eye(2)*1e-10,B.T@residual)
            value=-float(coef@(B.T@residual))
            return (value,coef,B) if return_parts else value
        candidates=[]
        for d0 in (2.,12.,60.,250.):
            opt=optimize.minimize(objective,[f0,math.log(d0)],method='L-BFGS-B',
                bounds=[(max(80,f0-25),min(18000,f0+25)),(math.log(.1),math.log(4000))],
                options={'maxiter':35,'ftol':1e-9})
            candidates.append(opt)
        opt=min(candidates,key=lambda r:r.fun);f,d=float(opt.x[0]),float(np.exp(opt.x[1]))
        _,coef,B=objective(opt.x,True)
        rows.append([f,d,float(coef[0]),float(coef[1])]);residual-=B@coef
        history.append(float(np.linalg.norm(residual)/np.linalg.norm(y)))
        if history[-1]<.025: break
    # Solve all modal residues together. Noise/background remains as residual;
    # no discarded reference residual is stored or spliced into new generations.
    B=np.column_stack([basis(f,d) for f,d,_,_ in rows])
    coefficients=np.linalg.lstsq(B,y,rcond=1e-7)[0]
    for i,row in enumerate(rows): row[2:]=coefficients[2*i:2*i+2].tolist()
    model={'schema':SCHEMA,'sample_rate':RATE,'calibrated_force_to_pressure':False,'modes':rows,
           'runtime_recording_reads':False,'geometry_identified':False,'model_type':'effective damped modal microphone response',
           'fit':{'method':'greedy variable projection and joint linear residues','training_only':True,'preprocessing':prep,
                  'relative_waveform_residual':float(np.linalg.norm(y-B@coefficients)/np.linalg.norm(y)),
                  'greedy_residual_history':history,'no_residual_recording_retained':True}}
    validate(model);return model

def generic_prior(object_id):
    """Unmeasured coarse oscillator prior; not a scanned physical geometry."""
    params={'27_WoodPlate':(650,35,1.6),'64_CeramicMug':(1300,5,1.45),'94_GlassGoblet':(950,1.8,1.55)}
    f,d,spacing=params[object_id]
    modes=[[f*spacing**i,d*(1+i*.35),0.,1./(1+i)] for i in range(7) if f*spacing**i<16000]
    return {'schema':SCHEMA,'sample_rate':RATE,'calibrated_force_to_pressure':False,'modes':modes,
            'object_id':object_id,'model_type':'unmeasured modal prior','geometry_identified':False}

def metrics(candidate, reference):
    """Normalized spectral/decay diagnostics; not calibrated loudness or ASMR."""
    a=np.asarray(candidate,float);b=np.asarray(reference,float)
    if a.shape!=b.shape or a.ndim!=1 or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Equal finite mono arrays required')
    if min(np.linalg.norm(a),np.linalg.norm(b))<1e-12:raise ValueError('Silent input is not fidelity evidence')
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    edges=100*2**(np.arange(90)/12);freq=np.fft.rfftfreq(len(a),1/RATE)
    powers=[abs(np.fft.rfft(x))**2 for x in (a,b)]
    bands=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        if hi>16000: break
        m=(freq>=lo)&(freq<hi)
        bands.append([float(p[m].sum()) for p in powers])
    bands=np.array(bands);bands/=bands.sum(axis=0)
    active=bands[:,1]>1e-4
    db=10*np.log10(np.maximum(bands,1e-8));edcs=[]
    for x in (a,b):
        edc=np.cumsum(x[::-1]**2)[::-1];edcs.append(edc/max(edc[0],1e-15))
    return {'normalized_band_rmse_db':float(np.sqrt(np.mean((db[active,0]-db[active,1])**2))),
            'active_bands':int(active.sum()),'power_shape_l1':float(abs(bands[:,0]-bands[:,1]).sum()),
            'normalized_energy_decay_rmse':float(np.sqrt(np.mean((edcs[0]-edcs[1])**2))),
            'level_calibrated':False,'gain_normalization':'one energy scalar per mono comparison',
            'frequency_range_hz':[100,16000], 'weak_bands_excluded_below_fraction':1e-4}

NOISE_EDGES = np.geomspace(100,16000,17)
NOISE_DECAYS = np.array([8.,32.,128.,512.])

def _noise_band(lo, hi, n, rng):
    sos=signal.butter(2,[lo,hi],fs=RATE,btype='bandpass',output='sos')
    impulse=np.zeros(4096);impulse[0]=1
    norm=np.sqrt(np.sum(signal.sosfilt(sos,impulse)**2))
    return signal.sosfilt(sos,rng.standard_normal(n))/norm

def fit_residual(model, measurement):
    """Fit a bounded stochastic residual, NOT an identified friction mechanism.

    Only 16 band-power mixtures of four fixed decays are saved. Late measurement
    noise is subtracted before fitting. There is no retained residual waveform.
    """
    validate(model)
    y,_=crop_measurement(measurement);residual=y-impulse_response(model,1.5)
    block=96;t=(np.arange(len(y)//block)+.5)*block/RATE
    basis=np.exp(-2*t[:,None]*NOISE_DECAYS[None,:]);coeffs=[]
    for lo,hi in zip(NOISE_EDGES[:-1],NOISE_EDGES[1:]):
        sos=signal.butter(2,[lo,hi],fs=RATE,btype='bandpass',output='sos')
        z=signal.sosfilt(sos,residual)
        p=(z[:len(t)*block]**2).reshape(-1,block).mean(axis=1)
        floor=float(np.median(p[-100:]));target=np.maximum(0,p-floor)
        c,_=optimize.nnls(basis,target);coeffs.append(c.tolist())
    model=dict(model);model['residual']={'type':'fresh bandlimited stochastic impact residual',
        'band_edges_hz':NOISE_EDGES.tolist(),'amplitude_decays_per_s':NOISE_DECAYS.tolist(),
        'band_variance_weights':coeffs,'gain':1.,'mechanism_identified':False,
        'warning':'Measurement-derived transient texture; not calibrated contact-force noise.'}
    # One aggregate variance scale for the residual's measured energy; the
    # discarded residual waveform is not serialized or accepted by the renderer.
    new=noise_response(model,seconds=1.5,seed=901)
    usable=signal.sosfilt(signal.butter(4,16000,fs=RATE,output='sos'),residual)
    model['residual']['gain']=float(min(4.,np.linalg.norm(usable)/max(np.linalg.norm(new),1e-12)))
    model['model_type']='data-assisted modes plus statistical transient residual'
    return model

def noise_response(model,seconds=1.5,seed=901):
    validate(model)
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not .01<=seconds<=12:raise ValueError('Invalid duration')
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid seed')
    if 'residual' not in model: return np.zeros(round(seconds*RATE))
    p=model['residual'];edges=np.asarray(p['band_edges_hz']);decays=np.asarray(p['amplitude_decays_per_s']);weights=np.asarray(p['band_variance_weights'])
    if edges.shape!=(17,) or decays.shape!=(4,) or weights.shape!=(16,4) or not np.isfinite(weights).all() or np.any(weights<0) or np.max(weights)>10 or not np.array_equal(edges,NOISE_EDGES) or not np.array_equal(decays,NOISE_DECAYS):raise ValueError('Invalid residual statistics')
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid seed')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not .01<=seconds<=12:raise ValueError('Invalid duration')
    gain=p['gain']
    if type(gain) not in (int,float) or not math.isfinite(gain) or not 0<=gain<=4:raise ValueError('Invalid residual gain')
    n=round(seconds*RATE);t=np.arange(n)/RATE;rng=np.random.default_rng(seed);out=np.zeros(n)
    for i,(lo,hi) in enumerate(zip(edges[:-1],edges[1:])):
        envelope=np.sqrt(np.exp(-2*t[:,None]*decays)@weights[i])
        out+=_noise_band(lo,hi,n,rng)*envelope
    return out*gain

def render_hybrid(model,events,seconds=6.,*,seed=902,damping_scale=1.):
    y=render(model,events,seconds,damping_scale=damping_scale)
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('Invalid seed')
    for i,(at,strength,width) in enumerate(events):
        count=min(round(1.5*RATE),len(y)-round(at*RATE))
        noise=noise_response(model,1.5,(seed+i)%2**32)
        n=max(1,round(width*RATE));pulse=np.sin(np.pi*(np.arange(n)+.5)/n);pulse*=strength/pulse.sum()
        noise=signal.fftconvolve(noise,pulse)[:count]
        start=round(at*RATE);y[start:start+count]+=noise
    return y
