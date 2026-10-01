#!/usr/bin/env python3
"""Named stereo research auditions: ringing, source rotation, predicted near field.

Uses the common mechanical engine and the generic signed-emitter radiation
operator. Source arrays are synthesized, never fitted to/replayed from a fork
recording. Output levels are matched for timbre comparison, not physical SPL.
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.unified import SimulationEngine
from ku100sim.binaural import require_binaural


def case(f=512, *, near=False, rotating=False, side='right', monopole=False, duration=10):
    """Illustrative free resonators, not calibrated steel/weighted medical forks."""
    k0=.002*(2*np.pi*f)**2;k1=.0005*(2*np.pi*f*6.26)**2
    mechanics={'schema':'shared-mechanics/1','name':'Generic compact modal radiator',
        'duration_s':duration,'internal_rate':192000,'nodes':[
            {'id':'fundamental','mass_kg':.002,'k2_n_m':k0,'damping_n_s_m':.0008,'limit_m':.001,
             'initial':{'q_m':1e-5},'readout_weight':1.},
            {'id':'higher','mass_kg':.0005,'k2_n_m':k1,'damping_n_s_m':.012,'limit_m':.001,
             'initial':{'q_m':2e-8},'readout_weight':.12}],
        'evidence':{'status':'unmeasured_reduced_model','limits':'Already-ringing modes with assumed frequency, damping, initial state and signed-source map. No contact or identified fork geometry.'}}
    # Symmetric opposed dipoles. Geometry does not depend on the filename.
    elements=[[0,0,0,1]] if monopole else [[-.016,0,0,1],[-.006,0,0,-1],[.006,0,0,-1],[.016,0,0,1]]
    r=.1175 if near else .25;sign=-1 if side=='right' else 1
    radiation={'schema':'compact-modal-radiation/1','head_radius_m':.0875,
        'center_knots':[[0,0,sign*r,0],[duration,0,sign*r,0]],
        'angle_knots_deg':[[0,0],[duration,540 if rotating else 0]],
        'mode_elements':{'fundamental':elements,'higher':elements},'control_rate_hz':240}
    return {'mechanics':mechanics,'radiation':radiation}


def write_audio(path,a):
    data=io.BytesIO();wavfile.write(data,48000,a.astype(np.float32));raw=data.getvalue();path.write_bytes(raw)
    return {'sha256':hashlib.sha256(raw).hexdigest(),'frames':len(a),'sample_rate':48000,'channels':2,'bytes':len(raw)}


def build(out):
    out=Path(out)
    if out.exists():raise ValueError('Use a new output directory')
    out.mkdir(parents=True);rows=[];started=time.time()
    cases=[
        ('ring-only-512','512 Hz · longer ringing only',case(monopole=True),'Same point-source assumption, with slower damping. No rotation.'),
        ('rotate-anchor-512','512 Hz · rotate at 25 cm head-center radius',case(rotating=True),'New source directivity. Receiver anchored at the previously measured distance. Not a 25 cm ear gap.'),
        ('rotate-near-512','512 Hz · predicted close rotating field',case(near=True,rotating=True),'3 cm from modeled sphere surface to source center; closest element 1.4 cm. NOT a new measured KU100 position.'),
        ('rotate-near-256','256 Hz · predicted close rotating field',case(f=256,near=True,rotating=True),'Same operator, lower mechanical resonance; not EQ or time-stretching.'),
        ('rotate-near-128','128 Hz · predicted close rotating field',case(f=128,near=True,rotating=True),'Lower resonator hypothesis, NOT an identified weighted fork. Receiver data below ~200 Hz include analytic extension.'),
        ('rotate-near-left-256','256 Hz · predicted close field at left ear',case(f=256,near=True,rotating=True,side='left'),'Mirrored source position, evaluated with the actual separate left/right anchor filters.')]
    approach=case(f=256,near=True,rotating=True)
    approach['radiation']['center_knots']=[[0,0,-.25,0],[3.5,0,-.1175,0],[6.5,0,-.1175,0],[10,0,-.25,0]]
    approach['radiation']['angle_knots_deg']=[[0,0],[10,720]]
    cases.insert(0,('approach-rotate-256','256 Hz · approach, rotate, withdraw',approach,
        'A continuous distance/rotation gesture. Level changes inside this file come from the predicted field, not a volume-envelope effect.'))
    for slug,title,s,description in cases:
        print(slug,flush=True)
        with SimulationEngine(s['mechanics']) as engine:y,report=engine.render_radiated(s['radiation'])
        # One scalar per stereo audition, no per-ear normalization/limiter/EQ.
        rms=float(np.sqrt(np.mean(y*y)));peak=float(np.max(abs(y)))
        if rms<=1e-14:raise ValueError('Silent audition')
        gain=min(.04/rms,.35/peak);audio=y*gain
        identity=write_audio(out/(slug+'.wav'),audio)
        (out/(slug+'.scene.json')).write_text(json.dumps(s,indent=2,allow_nan=False)+'\n')
        report['listening_gain']=gain;report['listening_policy']='Each full stereo waveform RMS-matched to 0.04, with shared static peak cap 0.35; NO absolute SPL or physical pressure claim.'
        report['export']=identity;report['output_stereo']=require_binaural(audio)
        (out/(slug+'.report.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        # Envelope at 120 Hz for a display of the actual rendered audio, not a
        # fake visible 512-Hz physical motion.
        hop=400;blocks=audio[:len(audio)//hop*hop].reshape(-1,hop,2)
        envelope=np.sqrt(np.mean(blocks*blocks,axis=1))
        rows.append({'id':slug,'title':title,'description':description,'file':slug+'.wav',
            'scene':slug+'.scene.json','report':slug+'.report.json','listening_gain':gain,
            'rms':float(np.sqrt(np.mean(audio**2))),'peak':float(abs(audio).max()),**identity,
            'envelope_hz':120,'envelope':envelope.tolist()})
    manifest={'schema':'fork-radiation-auditions/1','application_baseline':'51f8390e6687d590ca53c8e9f97221d9d6807f67',
       'runtime':'Shared SimulationEngine plus generic CompactRadiation; not per-object renderers',
       'physical_pressure_calibrated':False,'human_listening_pass':None,'source_recordings_used':False,
       'source_materials_identified':False,'near_range_measurements_available':False,'mono_output_allowed':False,
       'capture':'Measured KU100 at 0.25 m anchors a rigid-sphere propagation prediction. Closer capture is unmeasured.',
       'elapsed_s':time.time()-started,'samples':rows,
       'limitations':['Not a tactile actuator/bone-conduction simulation','Free ringing only; not a mallet attack renderer',
            'Source arrays and mechanical initial states are illustrative','No full pinna geometry or moving-boundary wave solution',
            'Same-RMS listening copies remove absolute distance level change; diagnose orientation/timbre, not calibrated pressure']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    return manifest


def package_offline(folder,output):
    folder=Path(folder);m=json.loads((folder/'manifest.json').read_text())
    for row in m['samples']:row['audio_base64']=base64.b64encode((folder/row['file']).read_bytes()).decode()
    data=json.dumps(m,separators=(',',':')).replace('<','\\u003c')
    template=(ROOT/'web/fork-radiation/offline-template.html').read_text()
    core=(ROOT/'web/target/core.js').read_text()
    digest=core[core.index('export function portableDigest'):core.index('export function waveBytes')].replace('export ','')
    Path(output).write_text(template.replace('__DATA__',data).replace('__DIGEST__',digest))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--html',type=Path);a=p.parse_args()
    m=build(a.out)
    if a.html:package_offline(a.out,a.html)
    print(json.dumps({'samples':len(m['samples']),'elapsed_s':m['elapsed_s']}))
