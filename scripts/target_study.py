#!/usr/bin/env python3
"""Generate a narrow SOURCE discrimination study; never consumes reference audio at synthesis.

User WAVs are accepted by analyze_references only. Public JSON contains derived
measurements and original-file hashes, never reference samples. No ASMR or
physical-calibration score is fabricated.
"""
from __future__ import annotations
import argparse,base64,csv,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt,find_peaks,peak_widths
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.audio import read_wav,describe
from build_release import build

BANDS=[(20,250),(250,500),(500,2000),(2000,8000),(8000,20000)]
CASES=[('release-fast-left','Fast opening / left',{}),
       ('release-slow-left','Slow opening / left',{'--opening':'.02'}),
       ('release-vented-left','Never sealed / control',{'--control':'vented'}),
       ('release-fast-right','Fast opening / right',{'--azimuth':'270'})]

def descriptors(rate,x):
    result=describe(rate,x)
    # The onset labels below are detector events, not inferred tongue/peel/bubble actions.
    audible=sosfilt(butter(4,[40,min(18000,rate*.45)],fs=rate,btype='bandpass',output='sos'),x,axis=0)
    hop=max(1,round(rate*.002));n=len(x)//hop
    env=np.sqrt(np.mean(audible[:n*hop].reshape(n,hop,2)**2,axis=1));dominant=int(np.argmax(np.mean(audible**2,axis=0)))
    e=env[:,dominant];maxe=float(e.max()) if len(e) else 0
    threshold=maxe*10**(-30/20)
    peaks,_=find_peaks(e,prominence=maxe*.15,distance=max(1,round(.025*rate/hop))) if maxe else ([],{})
    widths=peak_widths(e,peaks,rel_height=.5)[0]*hop/rate if len(peaks) else np.array([])
    result['events']={'method':'2ms RMS, 40-18000Hz analysis only, prominence 15% of peak, separation 25ms',
        'dominant_channel':dominant,'detector_peak_times_s':(np.asarray(peaks)*hop/rate).tolist(),
        'detector_half_prominence_widths_s':widths.tolist(),'peaks_per_s':len(peaks)/(len(x)/rate),
        'activity_fraction_relative_minus30db':float(np.mean(e>threshold)) if maxe else 0,
        'causal_labels_available':False}
    result['envelope']={'hop_s':hop/rate,'values':env[::5].tolist(),'display_hop_s':hop*5/rate}
    return result

def generate(destination=None):
    dest=destination or ROOT/'web/target-study.json'
    binary=build();receipt=json.loads(binary.with_suffix('.build.json').read_text())
    bank=ROOT/'data/ku100_bank.bin'
    # Source-bank integrity is independently checked in existing preparation/CI.
    bank_hash=hashlib.sha256(bank.read_bytes()).hexdigest()
    if bank_hash!='8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712':raise ValueError('Unrecognized measured bank')
    cases=[]
    with tempfile.TemporaryDirectory(prefix='ku100-target-') as folder:
        for identifier,title,args in CASES:
            out=Path(folder)/identifier
            command=[str(binary),'--out',str(out),'--bank',str(bank)]
            for key,value in args.items():command.extend([key,value])
            subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
            raw=(out/'audio.wav').read_bytes();rate,x=read_wav(out/'audio.wav');native=json.loads((out/'native.json').read_text())
            if native['max_energy_residual_j']>max(1e-16,abs(native['work_j'])*1e-8):raise ValueError('Energy identity failed')
            if native['max_pressure_pa']>101325*.05 or native['peak_aperture_mach']>.05:raise ValueError('Small-signal screen failed')
            if np.max(abs(x))>=1:raise ValueError('Raw source observation exceeds digital full scale')
            trace=np.genfromtxt(out/'trace.csv',delimiter=',',names=True)
            rows=[[float(r[col]) for col in trace.dtype.names] for r in trace[::4]]
            cases.append({'id':identifier,'title':title,'kind':'generated-source-hypothesis',
                'native':native,'metrics':descriptors(rate,x),'audio':{'mime':'audio/wav','channels':2,'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()},
                'trace':{'columns':list(trace.dtype.names),'rows':rows},
                'limits':'Prescribed air-pocket wall/opening. Not saliva, tongue, contact transfer or identified reference source. Measured airborne KU100 receiver at 25cm.'})
    result={'version':'ku100-target-study/1','target':'Close nonverbal tongue–saliva interaction with artificial ear',
        'status':'source-discrimination experiment; full target not met','physical_target_accepted':False,
        'listener_assessment':None,'source_sha256':receipt['source_sha256'],'bank_sha256':bank_hash,
        'cases':cases,'reference_audio_included':False,
        'comparison_policy':'No fitting to recordings; no per-ear gain or delay optimization. Existing references reused diagnostically, not held-out validation.'}
    dest.parent.mkdir(exist_ok=True,parents=True);dest.write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    evidence=ROOT/'validation/local';evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'release-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
    compact={k:v for k,v in result.items() if k!='cases'}
    compact['cases']=[{k:v for k,v in case.items() if k not in {'audio','trace'}}|{'audio_sha256':case['audio']['sha256']} for case in cases]
    for case in compact['cases']:case['metrics'].pop('envelope',None)
    (evidence/'source-study.json').write_text(json.dumps(compact,indent=2,allow_nan=False)+'\n')
    return result

def analyze_references(folder:Path,output:Path):
    rows=[]
    # Frozen source-time crops. These recordings/excerpts have been inspected
    # before; they are diagnostic targets, not independent held-out data.
    for chapter,start in [('03',57.),('04',90.),('05',65.),('06',51.)]:
        matches=list(folder.glob(f'live_stream_019_chapter_{chapter}_*.wav'))
        if len(matches)!=1:raise ValueError('Expected exactly one recording for chapter '+chapter)
        source=matches[0];rate,x=read_wav(source);crop=x[round(start*rate):round((start+4)*rate)]
        if crop.shape!=(rate*4,2):raise ValueError('Missing stereo target interval')
        d=descriptors(rate,crop);d.pop('envelope')
        rows.append({'id':'chapter-'+chapter,'filename':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'start_s':start,'end_s':start+4,'start_frame':round(start*rate),'end_frame':round((start+4)*rate),
             'label_source':'uploaded chapter filename only','observed_action':'unverified; no synchronized action video',
             'device':'unverified','calibration':'unknown','source_processing':'unknown; do not assume original microphone PCM',
             'use':'previously inspected diagnostic target, not held-out test','metrics':d})
    result={'version':'ku100-reference-summary/1','reference_audio_included':False,'reference_count':len(rows),'references':rows,
        'physical_mechanism_identified':False,'no_fit':True,'purpose':'Compare acoustic descriptors and actual listening, not inferred tongue force'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--references',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args()
    if a.references:
        result=analyze_references(a.references,a.out or ROOT/'web/target-reference-summary.json')
        print(json.dumps({'references':result['reference_count'],'reference_audio_included':False}))
    else:
        result=generate(a.out);print(json.dumps({'cases':len(result['cases']),'physical_target_accepted':False}))
