"""Validated native-scene runner with exact input/output provenance receipts."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]

def run(scene,exe,out):
    allowed={'seconds','modes','oversample','action','side','receiver','coupling','viscosity','depth_um','speed','roughness_um','azimuth','distance'}
    if not isinstance(scene,dict) or set(scene)-allowed:raise ValueError('Unknown scene fields')
    args=[str(exe),'--out',str(out)];metadata={}
    receiver=scene.get('receiver','contact')
    if receiver not in ['contact','measured']:raise ValueError('Use contact or measured; sphere is a separate benchmark')
    if receiver=='measured':
        az=scene.get('azimuth',90);r=scene.get('distance',.25)
        if az not in [0,90,270] or r not in [.25,.5]:raise ValueError('Only verified bundled directions/distances accepted')
        path=ROOT/'assets'/f'ku100_{r:.2f}_{az}.txt';metadata=json.loads(path.with_suffix('.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['fir_sha256']:raise ValueError('Receiver checksum mismatch')
        args+=['--filter',str(path)]
    for k,v in scene.items():
        if k in ['azimuth','distance']:continue
        if not isinstance(v,(str,int,float)) or isinstance(v,bool):raise ValueError('Scene values must be scalar strings/numbers')
        args+=['--'+k.replace('_','-'),str(v)]
    subprocess.run(args,check=True,timeout=600)
    receipt={'scene':scene,'source_sha256':hashlib.sha256((ROOT/'src/sim.cpp').read_bytes()).hexdigest(),'receiver':metadata,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},'scope':'Fresh physical source; no measured contact calibration; no human listening verdict.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene',type=pathlib.Path);p.add_argument('--exe',type=pathlib.Path,default=ROOT/'build/ku100_sim');p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();run(json.loads(a.scene.read_text()),a.exe.resolve(),a.out)
