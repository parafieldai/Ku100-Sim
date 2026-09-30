#!/usr/bin/env python3
"""Seven parameter definitions -> ONE renderer -> generated-only web assets."""
import argparse,hashlib,json,shutil,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.render_unified import render_file
from ku100sim.unified import ROOT
# The demo manifest selects inputs and explicit listening gains, NOT algorithms.
EXAMPLES=[('fork-512',80.),('fork-256',80.),('fork-damped',80.),('plastic-snap',12.),('plastic-slow',12.),('silicone-sweep',24.),('silicone-hold',24.)]

def build(out):
    if out.exists():raise ValueError('Use new output')
    out.mkdir(parents=True)
    samples=[]
    with tempfile.TemporaryDirectory() as d:
        for slug,gain in EXAMPLES:
            target=Path(d)/slug
            report=render_file(ROOT/'scenes/unified'/f'{slug}.json',target,gain)
            scene=json.loads((target/'scene.json').read_text())
            row={'id':slug,'name':scene['name'],'description':scene.get('description',''),
                 'limitations':scene['evidence']['limits'],'seconds':scene['duration_s'],
                 'report':report,'scene':slug+'.json','audio':slug+'.wav'}
            for old,new in [('audio.wav',row['audio']),('scene.json',row['scene'])]:
                shutil.copyfile(target/old,out/new)
            # Small, real mechanical-state trace for inspection/visualization.
            import numpy as np
            data=np.loadtxt(target/'trace.csv',delimiter=',',skiprows=1)
            n=len(scene['nodes'])
            trace={'time_s':data[:,0].tolist(),'coordinates_m':data[:,1:1+n].tolist(),
                   'energy_j':data[:,-4].tolist(),'work_j':data[:,-3].tolist(),'dissipation_j':data[:,-2].tolist(),
                   'node_ids':[x['id'] for x in scene['nodes']]}
            row['trace']=slug+'-trace.json';(out/row['trace']).write_text(json.dumps(trace,separators=(',',':'),allow_nan=False))
            row['files_sha256']={fn:hashlib.sha256((out/fn).read_bytes()).hexdigest() for fn in (row['audio'],row['scene'],row['trace'])}
            samples.append(row);print(slug,report['render_seconds'],flush=True)
    m={'schema':'shared-mechanics-examples/1','single_engine':'SimulationEngine','source_recordings_included':False,
       'material_calibrated':False,'head_or_microphone_simulated':False,'samples':samples}
    (out/'manifest.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
    return m
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'web/unified/generated');a=p.parse_args();build(a.out)
