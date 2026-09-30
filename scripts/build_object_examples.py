#!/usr/bin/env python3
"""Generate named tapping examples from parameter-only object response models."""
from pathlib import Path
import argparse,hashlib,io,json,math,struct,sys,tempfile,shutil
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.modal_object import render_hybrid,generic_prior,RATE,validate
ITEMS=(('27_WoodPlate','wood-plate','Wood plate'),('64_CeramicMug','ceramic-mug','Ceramic mug'),('94_GlassGoblet','glass-goblet','Glass goblet'))
IDS=tuple(slug+'-'+kind for _,slug,_ in ITEMS for kind in ('sharp','soft','prior'))

def wav16(x):
    if x.ndim!=1 or not np.isfinite(x).all() or abs(x).max()>=.999:raise ValueError('Invalid mono preview')
    stereo=np.column_stack([x,x]);pcm=np.rint(stereo*32768).astype('<i2').tobytes()
    return b'RIFF'+struct.pack('<I',36+len(pcm))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,RATE,4*RATE,4,16)+b'data'+struct.pack('<I',len(pcm))+pcm

def build(out):
    out=Path(out).absolute()
    if out.exists() or out.is_symlink() or any(p.is_symlink() for p in out.parents):raise ValueError('New output path required')
    out.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.objects-',dir=out.parent))
    rows=[]
    try:
        for obj,slug,title in ITEMS:
            path=ROOT/'models/object-profiles'/f'{obj}.json';m=json.loads(path.read_text());validate(m)
            variants={}
            for kind,width in [('sharp',.00004),('soft',.00013)]:
                events=[(.25,.8,width),(1.3,1.,width),(2.6,.7,width)]
                with patch('builtins.open',side_effect=RuntimeError('No waveform or other files allowed during generation')),patch('numpy.load',side_effect=RuntimeError('No array recordings allowed')):
                    variants[kind]=(render_hybrid(m,events,4.,seed=7201),events)
            gain=min(.035/max(np.sqrt(np.mean(variants['sharp'][0]**2)),1e-12),.5/max(abs(v[0]).max() for v in variants.values()))
            with patch('builtins.open',side_effect=RuntimeError('No reference input')):
                prior=render_hybrid(generic_prior(obj),[(.1,1.,.00004)],1.)
            variants['prior']=(prior,[(.1,1.,.00004)])
            for kind,(x,events) in variants.items():
                scalar=gain if kind!='prior' else min(.035/max(np.sqrt(np.mean(x*x)),1e-12),.5/max(abs(x).max(),1e-12))
                # One scalar, identical ears. No hidden binaural coloration here.
                x=x*scalar
                # Preview-only 10 ms end fade avoids cutting a diagnostic prior tail.
                fade=round(.01*RATE);x[-fade:]*=.5*(1+np.cos(np.linspace(0,np.pi,fade)))
                raw=wav16(x);name=f'{slug}-{kind}.wav';(stage/name).write_bytes(raw)
                rows.append({'id':slug+'-'+kind,'object':obj,'title':title,'kind':kind,'file':name,
                    'sha256':hashlib.sha256(raw).hexdigest(),'frames':len(x),'rate':RATE,'channels':2,'pcm_bits':16,
                    'peak':float(abs(x).max()),'rms':float(np.sqrt(np.mean(x*x))),'gain':scalar,'events':events,
                    'model_type':'unmeasured illustrative prior' if kind=='prior' else m['model_type'],
                    'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if kind!='prior' else None})
        summary=json.loads((ROOT/'validation/objects/assessment.json').read_text())
        manifest={'schema':'object-sfx-preview/1','reference_audio_public':False,'old_ear_recordings_used':False,
                  'render_from_recording':False,'source_kind':'parameter-driven modes; optional generated stochastic residual',
                  'physical_calibration':False,'headphone_spatialization':'dual mono, not KU100 transfer','preview_end_fade_s':.01,
                  'pressure_control':False,'raw_reference_audio_embedded':False,'samples':rows,
                  'assessment':{r['object']:[v['summary'] for v in r['selected']] for r in summary['objects']},
                  'listener_judgment':'not performed','regeneration_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n');stage.replace(out)
        print(json.dumps({'out':str(out),'files':len(rows),'no_reference_reads':True}))
        return manifest
    finally:
        if stage.exists():shutil.rmtree(stage)
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'web/objects/generated');a=ap.parse_args();build(a.out)
