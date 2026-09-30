#!/usr/bin/env python3
"""Render ANY supported shared-mechanics JSON; object identity is never dispatch."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.unified import ROOT,SimulationEngine


def render_file(scene_path,out,gain=12.,stiffness_scale=1.,damping_scale=1.):
    from scripts.build_site import _read_file,_json
    s=_json(_read_file(scene_path,256*1024),'mechanical scene')
    if not .1<=stiffness_scale<=10 or not .1<=damping_scale<=10:raise ValueError('Parameter scale outside declared range')
    for node in s['nodes']:
        for k in ('k2_n_m','k4_n_m3'):node[k]=node.get(k,0)*stiffness_scale
        node['damping_n_s_m']=node.get('damping_n_s_m',0)*damping_scale
        if 'memory' in node:node['memory']['stiffness_n_m']*=stiffness_scale
        if 'driver' in node:node['driver']['stiffness_n_m']=node['driver'].get('stiffness_n_m',0)*stiffness_scale
    for edge in s.get('couplings',[]):edge['stiffness_n_m']*=stiffness_scale
    if out.exists() or out.is_symlink() or any(p.is_symlink() for p in out.absolute().parents):raise ValueError('Use a new regular output path')
    start=time.perf_counter()
    with SimulationEngine(s) as e:r=e.render_binaural(gain=gain)
    audio=r['audio']
    out.mkdir(parents=True,exist_ok=False);wavfile.write(out/'audio.wav',48000,audio)
    headers=['time_s']+[n['id']+'.q_m' for n in s['nodes']]+[n['id']+'.v_m_s' for n in s['nodes']]+[n['id']+'.memory_m' for n in s['nodes']]+['energy_j','work_j','dissipation_j','balance_j']
    np.savetxt(out/'trace.csv',r['trace'],delimiter=',',header=','.join(headers),comments='')
    (out/'scene.json').write_text(json.dumps(s,indent=2,allow_nan=False)+'\n')
    r['report'].update({'render_seconds':time.perf_counter()-start,'audio_file_sha256':hashlib.sha256((out/'audio.wav').read_bytes()).hexdigest(),
                       'listening_gain':gain,'preview_peak':float(abs(audio).max()),'preview_rms':float(np.sqrt(np.mean(audio**2))),
                       'preview_domain':'measured KU100 binaural capture of an uncalibrated compact velocity source; no contact calibration',
                       'stiffness_scale':stiffness_scale,'damping_scale':damping_scale})
    (out/'report.json').write_text(json.dumps(r['report'],indent=2,allow_nan=False)+'\n')
    return r['report']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--gain',type=float,default=12.);p.add_argument('--stiffness-scale',type=float,default=1.);p.add_argument('--damping-scale',type=float,default=1.);a=p.parse_args()
    print(json.dumps(render_file(a.scene,a.out,a.gain,a.stiffness_scale,a.damping_scale),indent=2))
