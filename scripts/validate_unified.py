#!/usr/bin/env python3
"""Independent numerical/behavioral evidence. Never a perceptual pass label."""
import argparse,copy,hashlib,json,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.unified import SimulationEngine,ROOT

def validate(out):
    rows=[]
    for slug in ['fork-512','plastic-snap','silicone-sweep','silicone-hold']:
        path=ROOT/'scenes/unified'/f'{slug}.json';scene=json.loads(path.read_text());start=time.perf_counter()
        with SimulationEngine(scene) as e:a=e.render()
        refined=copy.deepcopy(scene);refined['internal_rate']=2*scene.get('internal_rate',192000)
        with SimulationEngine(refined) as e:b=e.render()
        # End-of-step sample times, not waveform-fitted alignment.
        x=a['velocity'];y=b['velocity'][1::2]
        err=float(np.linalg.norm(x-y)/max(np.linalg.norm(y),1e-15))
        row={'scene':slug,'parameter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'coarse':a['report'],'refined':b['report'],'velocity_relative_l2':err,
             'temporal_refinement_pass':err<.01,'elapsed_s':time.perf_counter()-start}
        if a['report']['relative_balance_error']>1e-6:raise AssertionError('Energy accounting regression')
        if not row['temporal_refinement_pass']:raise AssertionError(f'Time refinement exceeded 1%: {slug} {err}')
        if slug=='plastic-snap':
            crossings=a['report']['zero_crossings'];row['bistable_transitions_per_node']=crossings
            if any(n!=3 for n in crossings):raise AssertionError('Expected three state-driven transitions per cell')
        if slug.startswith('silicone'):
            rate=scene.get('internal_rate',192000)
            quiet=np.sqrt(np.mean(x[int(5.6*rate):int(5.9*rate)]**2))
            active=np.sqrt(np.mean(x[int(.5*rate):int(1.4*rate)]**2))
            row['settled_to_active_rms']=float(quiet/max(active,1e-15))
            if quiet>max(1e-10,active*.001):raise AssertionError('Unexpected sustained output after release')
        rows.append(row);print(slug,'temporal error',err,flush=True)
    report={'schema':'shared-mechanics-validation/1','passed':True,'numerical_relative_l2_limit':.01,
            'calibrated_material':False,'human_listening_assessed':False,'recording_comparison_performed':False,
            'spatial_geometry_convergence_established':False,'tests':rows,
            'scope':'Same declared reduced graph, doubled timestep resolution; not a converged shell or a microphone test.'}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'validation/local/unified-validation.json');a=p.parse_args();validate(a.out)
