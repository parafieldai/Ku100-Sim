#!/usr/bin/env python3
"""Fit one measurement per item, freeze profiles, then compare other distances.

Validation rows were previously inspected in the prototype. This is a
reproducible development distance-transfer test, not a new blind benchmark.
"""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.modal_object import (fit_modes,fit_residual,crop_measurement,
    impulse_response,noise_response,metrics,generic_prior,RATE)
OBJECTS=('27_WoodPlate','64_CeramicMug','94_GlassGoblet')

def assess_model(m, data):
    rows=[]
    for i,x in enumerate(data):
        target,prep=crop_measurement(x)
        variants=[metrics(impulse_response(m,1.5)+noise_response(m,1.5,seed),target) for seed in (902,1701,9917)]
        summary={key:float(np.median([v[key] for v in variants])) for key in ('normalized_band_rmse_db','power_shape_l1','normalized_energy_decay_rmse')}
        summary['screen_pass']=summary['normalized_band_rmse_db']<=6 and summary['normalized_energy_decay_rmse']<=.15
        rows.append({'source_row':(7,22,37,52)[i],'used_to_fit':i==0,'onset_rule':prep,'seed_metrics':variants,'summary':summary})
    return rows

def run(data_root, output, report_path, reuse_modes=None):
    if output.exists():raise ValueError('Refusing to overwrite profiles')
    output.mkdir(parents=True)
    report={'schema':'object-impact-assessment/1','objects':[],
      'source':'RealImpact force-deconvolved measurements, 48 kHz',
      'training_row':7,'validation_rows':[22,37,52], 'validation_previously_inspected':True,
      'fit_policy':'24 modes; optional noise layer selected using training spectral RMSE only',
      'criterion':{'normalized_band_rmse_db_at_most':6,'energy_decay_rmse_at_most':.15,'meaning':'Engineering screen, not perceptual realism or ASMR'},
      'full_recording_simulator_validated':False,'human_listening_performed':False,
      'notes':['No raw hammer trace is present in these published ZIPs; cannot reverify force deconvolution or calibrate N to Pa.',
               'Only one impact vertex/azimuth/height and four distances per object.',
               'Scores normalize overall energy and exclude weak bands; they do not validate level or full sound field.']}
    for name in OBJECTS:
        folder=data_root/name;src=folder/'deconvolved_0db.npy';data=np.load(src,allow_pickle=False)
        if data.ndim!=2 or data.shape[0]!=4:raise ValueError('Wrong measurement population')
        m=(json.loads((reuse_modes/(name+'.json')).read_text()) if reuse_modes else fit_modes(data[0],24))
        m.pop('residual',None);m['object_id']=name
        hybrid=fit_residual(m,data[0]);target,_=crop_measurement(data[0])
        modal_train=metrics(impulse_response(m,1.5),target)['normalized_band_rmse_db']
        hybrid_train=float(np.median([metrics(impulse_response(hybrid,1.5)+noise_response(hybrid,1.5,seed),target)['normalized_band_rmse_db'] for seed in (902,1701,9917)]))
        selected=hybrid if hybrid_train<modal_train else m
        selected['model_type']='data-assisted modes plus statistical transient residual' if 'residual' in selected else 'data-assisted damped modal response'
        selected['provenance']={'dataset':'RealImpact, Clarke et al., CVPR 2023','project':'https://samuelpclarke.com/realimpact/',
          'object':name,'source_array':'deconvolved_0db.npy','subset_file_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
          'original_training_row':7,'training_array_row':0,'sample_rate':RATE,
          'listener_xyz_m':np.load(folder/'listenerXYZ.npy',allow_pickle=False)[0].tolist(),
          'vertex_id':int(np.load(folder/'vertexID.npy',allow_pickle=False)[0]),
          'original_ear_recordings_used':False,'processing':'Author hammer-deconvolved response; fitted after declared onset, high-pass and level normalization.'}
        path=output/(name+'.json');path.write_text(json.dumps(selected,indent=2,allow_nan=False)+'\n')
        row={'object':name,'selected_model':selected['model_type'],'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'training_selection_rmse_db':{'modal':modal_train,'with_residual':hybrid_train},
          'listener_positions_m':np.load(folder/'listenerXYZ.npy',allow_pickle=False).tolist(),
          'baseline':assess_model(generic_prior(name),data),'selected':assess_model(selected,data)}
        report['objects'].append(row)
        print(name,row['selected_model'],[round(r['summary']['normalized_band_rmse_db'],2) for r in row['selected']],flush=True)
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--reuse-modes',type=Path);a=ap.parse_args()
    run(a.data,a.out,a.report,a.reuse_modes)
