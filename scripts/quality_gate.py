#!/usr/bin/env python3
"""Per-ear and per-band main-model refinement, with explicit unassessed bands.

An assessment can complete successfully while fidelity remains unestablished.
Thresholds are engineering diagnostics, not audibility or ASMR thresholds.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
BANDS=[(20,250),(250,500),(500,2000),(2000,8000),(8000,20000)]

def compare(x,y,rate,tolerance=.005,weak_fraction=1e-5):
    if x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Expected equal finite stereo arrays')
    # Fixed source-time interval, no waveform-fitted delay, phase or level.
    a,b=int(.12*rate),int(.55*rate)
    if len(x)<b:raise ValueError('At least 0.55 seconds is required')
    w=np.hanning(b-a)[:,None];fx=np.fft.rfft(x[a:b]*w,axis=0);fy=np.fft.rfft(y[a:b]*w,axis=0)
    freq=np.fft.rfftfreq(b-a,1/rate);power=abs(fy)**2;err=abs(fx-fy)**2
    total=power[(freq>=20)&(freq<20000)].sum(axis=0)
    rows=[]
    for lo,hi in BANDS:
        mask=(freq>=lo)&(freq<hi);p=power[mask].sum(axis=0);e=err[mask].sum(axis=0)
        fraction=np.divide(p,total,out=np.zeros(2),where=total>0)
        relative=np.sqrt(np.divide(e,p,out=np.zeros(2),where=p>0))
        status=['unassessed-weak-excitation' if total[i]==0 or fraction[i]<weak_fraction else 'pass' if relative[i]<=tolerance else 'fail' for i in range(2)]
        rows.append({'hz':[lo,hi],'relative_l2':[float(relative[i]) if p[i]>0 else None for i in range(2)],'reference_power_fraction':fraction.tolist(),'status':status})
    norm=np.linalg.norm(y,axis=0);rel=np.linalg.norm(x-y,axis=0)/np.maximum(norm,1e-300)
    return {'whole_waveform_relative_l2':rel.tolist(),'bands':rows,'all_bands_verified':all(s=='pass' for row in rows for s in row['status'])}

def assess(work):
    source=ROOT/'tests/quality_probe.cpp';binary=work/'probe';raw=work/'raw';raw.mkdir()
    subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-I',str(ROOT/'native'),str(source),str(ROOT/'native/physics.cpp'),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary),str(raw)],check=True,capture_output=True,text=True,timeout=1200)
    records=[json.loads(line) for line in result.stdout.splitlines()];lookup={r['name']:r for r in records}
    signals={r['name']:np.fromfile(raw/(r['name']+'.f64'),dtype=np.float64).reshape(-1,2) for r in records}
    for row in records:
        x=signals[row['name']]
        if not np.isfinite(x).all() or len(x)!=row['frames'] or not row['regime_valid']:raise AssertionError('Physical integrity failure: '+row['name'])
        if row['energy_j']<0 or row['loss_j']<0 or row['max_residual_j']>max(1e-14,abs(row['work_j'])*1e-8):raise AssertionError('Work accounting failed: '+row['name'])
        row['raw_pressure_sha256']=hashlib.sha256(x.astype('<f8').tobytes()).hexdigest()
    mirror=float(np.max(abs(signals['viscous128']-signals['mirror'][:,::-1])))
    if mirror>1e-8 or np.any(signals['silence']):raise AssertionError('Unsteady model failed silence/mirror invariants')
    pairs=[('viscous128','viscous256'),('viscous256','viscous512'),('fine256','fine512'),('fine512','fine1024'),('viscous128','viscous128-r384'),('fine512','fine512-r384')]
    comparisons=[]
    for coarse,fine in pairs:
        rate=lookup[coarse]['sample_rate'];factor=lookup[fine]['sample_rate']//rate
        y=signals[fine][factor-1::factor] # End-of-step source times; not a fitted alignment.
        comparisons.append({'coarse':coarse,'fine':fine,**compare(signals[coarse],y,rate)})
    sensitivity=compare(signals['legacy128'],signals['viscous128'],192000)
    sensitivity['meaning']='Change of physical loss model, NOT a discretization error or fidelity score'
    return {'schema':'main-quality-assessment/1','generated_utc':datetime.now(timezone.utc).isoformat(),'assessment_completed':True,'physical_integrity_checks_passed':True,
            'numerical_policy':{'relative_l2_tolerance':.005,'weak_reference_power_fraction':1e-5,'window':'Hann, fixed 0.12 to 0.55 s','per_ear':True,'gain_fit':False,'delay_fit':False,'limits':'Finite trajectories only; an unexcited band is unassessed, never a pass'},
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,ROOT/'native/physics.cpp',ROOT/'native/physics.hpp',ROOT/'native/viscous.hpp',Path(__file__)]},
            'runs':records,'mirror_max_error_pa':mirror,'comparisons':comparisons,'unsteady_loss_sensitivity':sensitivity,'full_band_contact_fidelity_established':False,'human_listening_assessment':'not performed'}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'validation/local/quality-assessment.json');ap.add_argument('--keep-work',type=Path);args=ap.parse_args()
    if args.keep_work:args.keep_work.mkdir(parents=True,exist_ok=False);report=assess(args.keep_work)
    else:
        with tempfile.TemporaryDirectory() as folder:report=assess(Path(folder))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'report':str(args.out),'assessment_completed':True,'physical_integrity_checks_passed':True,'full_band_contact_fidelity_established':False}))
