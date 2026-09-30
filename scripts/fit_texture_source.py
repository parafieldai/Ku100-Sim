#!/usr/bin/env python3
"""Fit aggregate source texture, without exporting source waveforms or timelines."""
from pathlib import Path
import argparse,hashlib,json,sys,lzma
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.audio import read_wav
from ku100sim.texture_source import fit,RATE,pack

def run(path,side,reference=False):
    rate,x=read_wav(path);ear=int(side=='right')
    ranges=([(57,63)] if side=='right' else [(89,95)]) if reference else ([(0,50),(70,120)] if side=='right' else [(0,82),(102,184)])
    if rate!=44100 or len(x)<max(b for a,b in ranges)*rate:raise ValueError('Unexpected original reference')
    chunks=[]
    for a,b in ranges:
        y=signal.resample_poly(x[round(a*rate):round(b*rate),ear],160,147)
        # This removes slow/DC recording offsets identically across entire ranges,
        # not at separate detected events. No event peak normalization.
        y=signal.sosfilt(signal.butter(3,35,fs=RATE,btype='high',output='sos'),y)
        chunks.append(y)
    return fit(chunks,{'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'ranges_s':ranges,'source_rate':rate,'near_channel':ear,'side':side,
        'fit_scope':'reference_excerpt' if reference else 'disjoint_ranges',
        'evaluation_role':'Same-excerpt texture representation, not held-out prediction' if reference else 'Range-fitted source; comparison windows excluded but previously inspected',
        'comparison_excluded_s':None if reference else ([50,70] if side=='right' else [82,102]),
        'preprocessing':'resample_poly 160/147; continuous 35 Hz Butterworth high-pass, order 3',
        'status':'User-supplied processed audio; hardware/action/forces unverified',
        'target_sample_sequence_exported':False,'comparison_previously_inspected':True})
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--side',choices=['left','right'],required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--reference',action='store_true');a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite a fitted model')
    m=run(a.input,a.side,a.reference);a.out.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(m,separators=(',',':'),allow_nan=False)+'\n').encode();a.out.write_bytes(pack(m) if a.out.name.endswith('.ctm.xz') else lzma.compress(raw) if a.out.suffix=='.xz' else raw)
    print(json.dumps({'model':str(a.out),'training_seconds':m['training_frames']/RATE,'bytes':a.out.stat().st_size}))
