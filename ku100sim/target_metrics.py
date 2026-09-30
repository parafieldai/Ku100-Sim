"""Acoustic descriptors for a reference comparison; never a realism rating."""
from __future__ import annotations
import numpy as np
from scipy import signal
from ku100sim.burst_source import event_candidates
BANDS = [(20,250),(250,1000),(1000,4000),(4000,10000),(10000,20000)]


def stats(rate, audio):
    if type(rate) is not int or not 8000 <= rate <= 192000:raise ValueError('Invalid sample rate')
    y=np.asarray(audio,dtype=float)
    if y.ndim!=2 or y.shape[1]!=2 or len(y)<rate or not np.isfinite(y).all():raise ValueError('Need at least 1 s of finite stereo')
    f,p=signal.welch(y,fs=rate,nperseg=min(4096,len(y)),noverlap=2048,axis=0,detrend=False)
    band=np.array([p[(f>=a)&(f<b)].sum(0) for a,b in BANDS]);tot=band.sum(0)
    frac=np.divide(band,tot,out=np.zeros_like(band),where=tot>0)
    rms=np.sqrt(np.mean(y*y,axis=0));near=int(np.argmax(rms))
    ild=20*np.log10(rms[0]/rms[1]) if np.all(rms>0) else None
    # Fixed common signal processing; not measured source pressure or material properties.
    if np.all(rms>0):
        _, coh=signal.coherence(y[:,0],y[:,1],fs=rate,nperseg=1024)
    else:coh=np.array([np.nan])
    return {'duration_s':len(y)/rate,'sample_rate_hz':rate,'rms':rms.tolist(),
            'rms_dbfs':[float(20*np.log10(v)) if v>0 else None for v in rms],
            'ild_left_minus_right_db':float(ild) if ild is not None else None,
            'audio_bands_hz':BANDS,'band_power_fraction_per_ear':frac.T.tolist(),
            'sub_20hz_fraction':np.divide(p[f<20].sum(0),p.sum(0),out=np.zeros(2),where=p.sum(0)>0).tolist(),
            'acoustic_peak_rate_hz':len(event_candidates(y,rate,near))/(len(y)/rate),
            'peak':float(abs(y).max()),'full_scale_exceeded':bool(abs(y).max()>1),
            'coherence_mean_0_24k':float(np.nanmean(coh)) if np.isfinite(coh).any() else None}


def compare_stats(reference, candidate):
    a=np.array(reference['band_power_fraction_per_ear']); b=np.array(candidate['band_power_fraction_per_ear'])
    # No global scalar combines spatial, texture, timing, or listening decisions.
    delta=[]
    for ear in range(2):
        delta.append([float(10*np.log10(max(b[ear,k],1e-12)/a[ear,k])) if a[ear,k]>=1e-5 else None for k in range(5)])
    li=reference['ild_left_minus_right_db'];ri=candidate['ild_left_minus_right_db']
    return {'ild_error_db':abs(li-ri) if li is not None and ri is not None else None,
            'relative_band_power_error_db_per_ear':delta,
            'detected_peak_rate_error_hz':candidate['acoustic_peak_rate_hz']-reference['acoustic_peak_rate_hz'],
            'waveforms_aligned':False,'perceptual_acceptance':'unassessed',
            'mechanical_controls_validated':False,'note':'Different event sequences; descriptor discrepancies only, no waveform-SNR/realism percentage.'}
