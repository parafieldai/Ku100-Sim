#!/usr/bin/env python3
"""Measure refinement without turning mesh/audio failures into a realism pass."""
from pathlib import Path
import json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.unified import SimulationEngine
from scripts.make_hand_scenes import scene

def run(cells,rate):
 s=scene(cells=cells,rate=rate,duration=1.5)
 with SimulationEngine(s) as engine:r=engine.render()
 nv=len(r['mesh']['rest'])+2;trace=r['trace']
 return {'report':r['report'],'time':trace[:,0],'forces':trace[:,1+6*nv:1+6*nv+2], 'flux':r['flux'], 'energy':trace[:,-7]}

def compare(a,b,rate_a,rate_b):
 # The arrays use end-of-step times. No fitted phase, gain, or time shift.
 step=rate_b//rate_a;bf=b['flux'][step-1::step];af=a['flux']
 force_b=np.column_stack([np.interp(a['time'],b['time'],b['forces'][:,c]) for c in range(2)])
 return {'force_relative_l2':(np.linalg.norm(a['forces']-force_b,axis=0)/np.maximum(np.linalg.norm(force_b,axis=0),1e-15)).tolist(),
         'surface_flux_relative_l2':float(np.linalg.norm(af-bf)/max(np.linalg.norm(bf),1e-20))}

def main(out):
 rows={}
 for label,cells,rate in [('coarse',[4,2,3],96000),('time_fine',[4,2,3],192000),('default',[6,3,4],96000),('mesh_fine',[8,4,6],96000)]:
  print('Refinement',label,flush=True);rows[label]=run(cells,rate)
 comp={'time96_192':compare(rows['coarse'],rows['time_fine'],96000,192000),'mesh_coarse_default':compare(rows['coarse'],rows['default'],96000,96000),'mesh_default_fine':compare(rows['default'],rows['mesh_fine'],96000,96000)}
 for label,r in rows.items():
  report=r['report'];peak=float(abs(r['energy']).max());report['balance_relative_to_peak_stored_energy']=report['max_balance_error_j']/max(peak,1e-12)
  if not np.isfinite(r['flux']).all() or report['min_jacobian']<=.45 or report['max_jacobian']>=1.55 or report['balance_relative_to_peak_stored_energy']>.01:
   raise AssertionError('Numerical integrity failure '+label)
 report={'schema':'hand-scene-refinement/1','interval_s':1.5,'trajectory_note':'A declared 1.5 s diagnostic ending partway through rubbing, not the whole five-second audition', 'comparisons':comp,'runs':{k:v['report'] for k,v in rows.items()},'criterion':{'temporal_force_relative_l2':.01,'spatial_force_relative_l2':.05,'spatial_source_flux_relative_l2':.05},'no_fit_gain_or_time_alignment':True,'held_out_recording_prediction':False,'asmr_acceptance':None,'pressure_sensation_established':False}
 report['temporal_force_check_passed']=max(comp['time96_192']['force_relative_l2'])<.01
 report['mesh_force_check_passed']=max(comp['mesh_default_fine']['force_relative_l2'])<.05
 report['mesh_source_check_passed']=comp['mesh_default_fine']['surface_flux_relative_l2']<.05
 if not report['temporal_force_check_passed']:raise AssertionError('Temporal force refinement failed')
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report['comparisons'],indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'validation/local/hand/refinement.json');a=p.parse_args();main(a.out)
