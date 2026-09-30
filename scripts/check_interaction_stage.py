#!/usr/bin/env python3
"""Verify the normal-grip stage; do not publish it as a silicone sound."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ku100sim.unified import SimulationEngine


def evaluate(out:Path):
    out.mkdir(parents=True,exist_ok=False)
    scene=json.loads((ROOT/'scenes/interactions/opposed-grip.json').read_text())
    with SimulationEngine(scene) as engine:
        base=engine.render();reactions=engine.interaction_readout(base['trace'][:,1:])
    fine=copy.deepcopy(scene);fine['internal_rate']*=2
    with SimulationEngine(fine) as engine:refined=engine.render()
    # Both arrays contain END-of-step source values, no fitted delay or gain.
    error=float(np.linalg.norm(base['velocity']-refined['velocity'][1::2])/np.linalg.norm(refined['velocity'][1::2]))
    if error>.005:raise AssertionError('Grip exceeded fixed 0.5% velocity time-refinement limit')
    for run in (base,refined):
        if run['report']['relative_balance_error']>1e-6:raise AssertionError('Energy balance failure')
    softer=copy.deepcopy(scene);softer['interactions'][0]['stiffness_n_m']*=.25
    with SimulationEngine(softer) as engine:
        soft=engine.render();changed=engine.interaction_readout(soft['trace'][:,1:])
    grip=base['trace'][:,0];hold=(grip>.9)&(grip<1.2)
    peak={name:float(row['force_n'].max()) for name,row in reactions.items()}
    held={name:float(np.mean(row['force_n'][hold])) for name,row in reactions.items()}
    new_held={name:float(np.mean(row['force_n'][hold])) for name,row in changed.items()}
    if abs(new_held['thumb_to_object']-held['thumb_to_object'])<.01*held['thumb_to_object']:
        raise AssertionError('Changing contact compliance did not affect coupled load')
    # Force endpoint evaluation, not integration's step-average force. Units SI.
    names=list(reactions);columns=['time_s']+[n['id']+'_q_m' for n in scene['nodes']]+[name+'_reaction_n' for name in names]
    trace=np.column_stack([grip,base['trace'][:,1:5],*(reactions[n]['force_n'] for n in names)])
    np.savetxt(out/'grip-trace.csv',trace,delimiter=',',header=','.join(columns),comments='')
    report={'schema':'interaction-stage/1','source_scope':'1D reduced normal grip, not 3D hand/fluid/ASMR rendering',
            'new_contact_laws':['normal_contact','viscoelastic_link'],
            'body_materials':[b['material'] for b in scene['bodies']],
            'velocity_refinement_relative_l2':error,'velocity_refinement_limit':.005,
            'baseline':base['report'],'fine':refined['report'],
            'peak_interaction_force_n':peak,'hold_interaction_force_n':held,
            'hold_after_contact_stiffness_quartered_n':new_held,
            'final_detached':all(not reactions[n]['in_contact'][-1] for n in ('thumb_to_object','index_to_object')),
            'new_audio_published':False,'recording_fitted':False,'water_implemented':False,
            'articulated_3d_hand_implemented':False,'tangential_friction_implemented':False,'human_listening_pass':False,
            'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'native/unified/engine.cpp',ROOT/'ku100sim/unified.py',ROOT/'scenes/interactions/opposed-grip.json']}}
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'refinement':error,'hold_force_n':held,'changed_force_n':new_held,'full_sound_model':False}))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    evaluate(parser.parse_args().out)
