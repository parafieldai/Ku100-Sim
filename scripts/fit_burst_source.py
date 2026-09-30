#!/usr/bin/env python3
"""Fit ONLY aggregate acoustic envelopes from explicitly selected supplied recordings.

No mechanical labels are created. The runtime model excludes source waveforms,
per-event parameters, event locations and reference timelines. Refit is explicit.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
from scipy import signal
from scipy.fft import rfft
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.audio import read_wav
from ku100sim.burst_source import SR, PHASES, NFFT, KNOTS, event_candidates, validate_model


def fit(path, ranges, near):
    rate,y=read_wav(path)
    if rate!=44100 or y.shape[1]!=2:raise ValueError('This frozen experiment expects the supplied 44.1 kHz stereo files')
    rows=[];durations=[];rms_values=[];candidates=[]
    for start,end in ranges:
        # Analyse windows separately: concatenation must not invent boundary transients.
        x=signal.resample_poly(y[round(start*rate):round(end*rate)],160,147,axis=0)
        for a,b,pk in event_candidates(x,SR,near):
            if a < round(.25*SR) or b>len(x)-round(.25*SR): continue
            z=signal.sosfilt(signal.butter(2,35,fs=SR,btype='high',output='sos'),x[a:b],axis=0)
            level=float(np.sqrt(np.mean(z[:,near]**2)))
            if level<1e-4:continue
            zz=np.pad(z,((NFFT//2,NFFT//2),(0,0)))
            event=[]
            for phase in range(PHASES):
                j=round(phase*(len(z)-1)/(PHASES-1))
                spectrum=rfft(zz[j:j+NFFT]*signal.windows.hann(NFFT,sym=False)[:,None],axis=0)
                event.append(abs(spectrum)**2/level**2)
            rows.append(event);durations.append(len(z)/SR);rms_values.append(level)
            candidates.append({'start_s':start+a/SR,'end_s':start+b/SR,'peak_s':start+pk/SR,
                              'label':'detector_candidate','physical_action':None})
    if len(rows)<20:raise ValueError('Insufficient detected events for this pooled experiment')
    power=np.mean(rows,axis=0);freq=np.fft.rfftfreq(NFFT,1/SR)
    spectra=[]
    for phase in range(PHASES):
        rr=[]
        for c in range(2):
            logmag=.5*np.log(np.maximum(power[phase,:,c],1e-12))
            logmag=signal.savgol_filter(logmag,17,2)
            # DC suppressed; very high band retained as estimated, not boosted to taste.
            logmag[0]=-14
            rr.append(np.interp(KNOTS,freq,logmag).round(6).tolist())
        spectra.append(rr)
    model={'schema':'empirical-burst-source/1','physical_model':False,'sample_rate_hz':SR,
           'near_channel':near,'log_magnitude':spectra,
           'duration_median_s':float(np.median(durations)),
           'duration_log_std':float(np.std(np.log(durations))),
           'rms_median':float(np.median(rms_values)),
           'rms_log_std':float(np.std(np.log(rms_values))),
           'detected_event_rate_hz':len(rows)/sum(b-a for a,b in ranges),
           'fitting':{'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                      'ranges_s':ranges,'detected_events':len(rows),'event_labels':'unverified acoustic candidates',
                      'device':'unverified','source_separated':False,'source_rate_hz':rate,
                      'phase_parameters':PHASES,'frequency_knots':len(KNOTS),
                      'windowing':'Hann / pooled power per event-life phase',
                      'preprocessing':'resample_poly 160/147; per-event 35 Hz Butterworth HP for fitting only',
                      'calibration':'none; captures source plus transmission plus recording processing',
                      'runtime_samples_or_event_timeline':False}}
    validate_model(model)
    return model,candidates


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--profile',choices=['right','left'],required=True)
    ap.add_argument('--event-audit',type=Path)
    args=ap.parse_args()
    if args.out.exists():raise SystemExit('Refusing to overwrite a fitted model')
    ranges=[(0,50),(70,120)] if args.profile=='right' else [(0,82),(102,184)]
    model,events=fit(args.input,ranges,int(args.profile=='right'))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(model,separators=(',',':'),allow_nan=False)+'\n')
    if args.event_audit:args.event_audit.write_text(json.dumps({'events':events},indent=2))
    print(json.dumps({'out':str(args.out),'events':len(events),'physical_model':False}))
