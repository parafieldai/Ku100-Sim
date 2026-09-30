#!/usr/bin/env python3
"""Render an empirical acoustic experiment, never a .ku100 physical bundle."""
from pathlib import Path
import argparse, hashlib, json, sys, tempfile, shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.burst_source import load_model, synthesize, wav_bytes
from ku100sim.audio import describe
ROOT=Path(__file__).resolve().parents[1]


def render(model_path, output, **kwargs):
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise ValueError('Refusing to overwrite output')
    if any(p.is_symlink() for p in output.parents):raise ValueError('Linked output parent is unsupported')
    model=load_model(Path(model_path))
    x,info=synthesize(model,**kwargs);raw=wav_bytes(x)
    if abs(x).max()>1:raise ValueError('Generated source exceeded full scale; no automatic limiter applied')
    info.update({'audio_sha256':hashlib.sha256(raw).hexdigest(),
                 'model_file_sha256':hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),
                 'source_sha256':hashlib.sha256((ROOT/'ku100sim/burst_source.py').read_bytes()).hexdigest(),
                 'metrics':describe(48000,x)})
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix='.burst-',dir=output.parent))
    try:
        (tmp/'audio.wav').write_bytes(raw)
        (tmp/'manifest.json').write_text(json.dumps(info,indent=2,allow_nan=False)+'\n')
        if output.exists():raise ValueError('Output appeared while rendering')
        tmp.rename(output)
    finally:
        if tmp.exists():shutil.rmtree(tmp)
    return info


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=6);p.add_argument('--seed',type=int,default=90291)
    p.add_argument('--rate-scale',type=float,default=1)
    p.add_argument('--gate-end',type=float)
    p.add_argument('--continuous-ablation',action='store_true')
    a=p.parse_args()
    result=render(a.model,a.out,seconds=a.seconds,seed=a.seed,rate_scale=a.rate_scale,gate_end=a.gate_end,continuous_ablation=a.continuous_ablation)
    print(json.dumps({'out':str(a.out),'physical_model':False,'audio_sha256':result['audio_sha256']}))
