#!/usr/bin/env python3
"""Full-duration refinement and source-field diagnostics, not listening scores."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.compact_radiation import CompactRadiation,array_free_field,sphere_green
from ku100sim.unified import SimulationEngine
from scripts.build_fork_radiation import case


def check():
    op=CompactRadiation();runs=[]
    for f in (128,256,512):
        s=case(f=f,near=True,rotating=True)
        with SimulationEngine(s['mechanics']) as e:a,report=e.render_radiated(s['radiation'])
        s['radiation']['control_rate_hz']=480
        with SimulationEngine(s['mechanics']) as e:b,_=e.render_radiated(s['radiation'])
        temporal=np.linalg.norm(a-b)/np.linalg.norm(b)
        per_ear=(np.linalg.norm(a-b,axis=0)/np.linalg.norm(b,axis=0)).tolist()
        assert max(per_ear)<.001
        s['mechanics']['internal_rate']=384000
        with SimulationEngine(s['mechanics']) as e:c,_=e.render_radiated(s['radiation'])
        step=np.linalg.norm(b-c)/np.linalg.norm(c)
        assert step<1e-6
        phi=np.arange(0,361,1.);centers=np.repeat([[0,-.1175,0]],len(phi),axis=0)
        h=op.response(f,centers,phi,s['radiation']['mode_elements']['fundamental'])
        hp=op.response(f,centers,phi,s['radiation']['mode_elements']['fundamental'],extra_terms=48)
        spatial=np.linalg.norm(h-hp)/np.linalg.norm(hp)
        assert spatial<1e-9
        runs.append({'frequency_hz':f,'seconds':10,'pose_240_to_480_hz_relative_l2':float(temporal),
            'pose_error_per_ear':per_ear,'mechanics_192_to_384_khz_relative_l2':float(step),
            'sphere_series_extra_48_terms_relative_l2':float(spatial),
            'modeled_rotation_magnitude_range_db':np.ptp(20*np.log10(abs(h)),axis=0).tolist(),
            'final_energy_balance_j':report['energy_balance_error_j']})
    angle=np.linspace(0,2*np.pi,720,endpoint=False);pattern=[]
    sources=[[-.016,0,0,1],[-.006,0,0,-1],[.006,0,0,-1],[.016,0,0,1]]
    for r in (.05,2):
        pts=np.column_stack([r*np.cos(angle),r*np.sin(angle),np.zeros(len(angle))])
        mag=abs(array_free_field(426,[[0,0,0]],[0],sources,pts)[0])
        peaks=signal.find_peaks(np.tile(mag,3),prominence=mag.max()*1e-3)[0]
        count=int(np.sum((peaks>=720)&(peaks<1440)))
        pattern.append({'range_m':r,'frequency_hz':426,'maxima_per_turn':count})
    assert [x['maxima_per_turn'] for x in pattern]==[4,2]
    alpha=.006/(2*.002);alpha_new=.0008/(2*.002)
    return {'schema':'fork-field-numerical-check/1','passed':True,'runs':runs,'free_field_directivity':pattern,
        'previous_fork':{'baseline_scene':'scenes/unified/fork-512.json at 51f8390', 'decay_per_s':alpha,
                        'three_second_amplitude_drop_db':float(20/np.log(10)*alpha*3),
                        'half_amplitude_s':float(np.log(2)/alpha)},
        'new_ring_setting':{'decay_per_s':alpha_new,'three_second_amplitude_drop_db':float(20/np.log(10)*alpha_new*3),
                           'material_calibrated':False},
        'criteria':{'max_pose_error_per_ear':.001,'max_step_error':1e-6,'max_series_error':1e-9},
        'scope':'Consistency of declared approximations only. No matched fork recording or human listening validation.',
        'matched_real_recording_validation':False,'asmr_acceptance':None,'haptic_output':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=check()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
