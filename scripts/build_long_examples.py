#!/usr/bin/env python3
"""Fresh 12 s texture takes and a 30 s overlap assembly; no recording playback.

All renders use the previously fitted aggregate model. The long example joins
three independent generated takes, not a continuous physical gesture simulation.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ku100sim.texture_source import load, synthesize, frozen_stereo_transfer, RATE
from ku100sim.burst_source import load_model, wav_bytes

SAMPLES=('fresh-right-a','fresh-right-b','fresh-left-a','long-right')

def join_fresh(parts, overlap):
    """Equal-power joins of independent, equal-length mono sections."""
    if len(parts)<2 or type(overlap) is not int or not 0<overlap<min(map(len,parts)):
        raise ValueError('Need independent sections and a bounded overlap')
    if any(np.asarray(x).ndim!=1 or not np.isfinite(x).all() for x in parts):
        raise ValueError('Expected finite mono sections')
    theta=np.linspace(0,np.pi/2,overlap)
    out=np.array(parts[0],dtype=float,copy=True)
    for part in parts[1:]:
        out=np.concatenate([out[:-overlap],out[-overlap:]*np.cos(theta)+part[:overlap]*np.sin(theta),part[overlap:]])
    return out

def finish(source, old):
    source=np.array(source,dtype=float,copy=True)
    fade=round(.01*RATE); w=.5-.5*np.cos(np.linspace(0,np.pi,fade))
    source[:fade]*=w;source[-fade:]*=w[::-1]
    stereo,route=frozen_stereo_transfer(old,source)
    audible=signal.sosfilt(signal.butter(3,35,fs=RATE,btype='high',output='sos'),stereo[:,old['near_channel']])
    rms=float(np.sqrt(np.mean(audible**2)));peak=float(abs(stereo).max())
    if rms<1e-9:raise ValueError('Degenerate generated audio')
    gain=min(.04/rms,.6/max(peak,1e-12));stereo*=gain
    if not np.isfinite(stereo).all() or abs(stereo).max()>.600001:raise ValueError('Invalid output')
    return stereo,route,gain

def build(out:Path, iterations=800):
    if out.exists() or out.is_symlink() or any(p.is_symlink() for p in out.absolute().parents):
        raise ValueError('Use a new output path')
    out.mkdir(parents=True)
    # Record the actual attempted audio reads, rather than trusting a manifest flag.
    reads=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=os.fsdecode(args[0]);mode=args[1];flags=args[2]
            writing=(isinstance(mode,str) and any(x in mode for x in 'wax')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR)))
            if p.lower().endswith(('.wav','.flac','.mp3','.m4a','.ogg','.opus','.aac')) and not writing:
                reads.append(p);raise RuntimeError('Recording read prohibited during synthesis')
    sys.addaudithook(audit)
    rows=[]; right=[]; histories=[];started=time.time()
    files={side:ROOT/f'models/texture-{side}-reference.ctm.xz' for side in ('right','left')}
    models={side:load(path) for side,path in files.items()}
    old={side:load_model(ROOT/f'models/burst-{side}.json') for side in files}
    def save(slug,title,side,x,info):
        y,route,gain=finish(x,old[side]);raw=wav_bytes(y);path=out/(slug+'.wav');path.write_bytes(raw)
        rows.append({'id':slug,'title':title,'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),
                     'source_seconds':len(x)/RATE,'frames':len(y),'sample_rate':RATE,'side':side,
                     'peak':float(abs(y).max()),'rms':np.sqrt(np.mean(y*y,axis=0)).tolist(),
                     'shared_listening_gain':gain,'fixed_stereo_route':route,'generation':info})
    for side,seed,label in [('right',5101,'a'),('right',5102,'b'),('right',5103,'c'),('left',5104,'a')]:
        print(f'Generating {side} seed={seed} 12 seconds, {iterations} iterations',flush=True)
        x,info=synthesize(models[side],seconds=12,seed=seed,iterations=iterations,boundary_fade=False)
        if info['best_objective']>=info['history'][0]['loss']*.5:raise ValueError('Optimizer did not improve its objective')
        info.update({'fitting_scope':models[side]['provenance']['fit_scope'],
                     'fitting_ranges_s':models[side]['provenance']['ranges_s'],
                     'source_model_file':files[side].name,'stored_model_sha256':hashlib.sha256(files[side].read_bytes()).hexdigest()})
        histories.append({'side':side,**info})
        if side=='right':right.append(x)
        if label!='c':save(f'fresh-{side}-{label}',f'Fresh {side} take {label.upper()} · 12 seconds',side,x,info)
        print(f'Done {side}-{label}: objective {info["best_objective"]:.5f}, elapsed {time.time()-started:.1f}s',flush=True)
    long=join_fresh(right,3*RATE)
    assert len(long)==30*RATE
    save('long-right','Long right texture · 30 seconds','right',long,{
        'method':'Three fresh 12 s generations, 3 s equal-power overlaps',
        'seeds':[5101,5102,5103],'section_starts_s':[0,9,18],'overlap_s':3,
        'repeats_recorded_or_generated_clip':False,'continuous_physical_state':False,
        'known_limit':'Joins can blend or interrupt event structures; no claim of seamless physical gestures.',
        'reuses_fresh_takes_a_b_in_this_bundle':True})
    m={'schema':'long-texture-examples/1','physical_model':False,'reference_audio_public':False,
       'source_recording_read_attempts':len(reads),'source_recording_reads':0,
       'source_reference_waveform_edited':False,'elapsed_render_s':time.time()-started,
       'source':{'description':'Aggregate statistics previously fitted to six-second reference excerpts, not new physical conditions.',
                 'code_sha256':hashlib.sha256((ROOT/'ku100sim/texture_source.py').read_bytes()).hexdigest(),
                 'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
       'samples':rows,'render_histories':histories,'human_listening_performed':False,
       'pressure_control_implemented':False}
    (out/'manifest.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'samples':len(rows),'seconds':m['elapsed_render_s'],'recording_read_attempts':len(reads)}),flush=True)
    return m
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--iterations',type=int,default=800);a=ap.parse_args()
    build(a.out,a.iterations)
