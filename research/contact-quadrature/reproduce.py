#!/usr/bin/env python3
"""Independent contact-quadrature diagnosis, not the production contact solver.

Default: integrate a smooth sphere against a flat plane with a closed-form
reference. --dynamic additionally copies the named production source to a new
scratch directory and tests denser quadrature there. Never edits the repository
kernel. No recording or artistic waveform parameters enter either experiment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

EXPECTED_KERNEL = '74f3a964245bf42af7e685b1d1cb523c5d42ab1762c22ed2c2499f40fdd1af5b'

def rule(level: int):
    triangles = [np.eye(3)]
    for _ in range(level):
        split = []
        for a,b,c in triangles:
            ab,bc,ca = (a+b)/2,(b+c)/2,(c+a)/2
            split.extend(np.array(t) for t in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
        triangles = split
    bary = np.concatenate([(np.eye(3)/2 + 1/6) @ t for t in triangles])
    weights = np.full(len(bary), 1/len(bary))
    np.testing.assert_allclose(bary.sum(axis=1), 1, atol=1e-15)
    np.testing.assert_allclose(weights.sum(), 1, atol=1e-15)
    return bary,weights

def static_check(box_mesh):
    rows = []
    for cells in [(4,2,3),(6,3,4),(8,4,6)]:
        x,_,faces,_,_ = box_mesh([.034,.008,.024], cells)
        xf = x[np.array([f for f in faces if np.max(abs(x[f,1]-.004))<1e-12])]
        area = np.linalg.norm(np.cross(xf[:,1]-xf[:,0],xf[:,2]-xf[:,0]),axis=1)/2
        for indentation in [.0007,.0018]:
            radius=.009; height=radius-indentation; layer_stiffness=60000/.002
            exact = np.pi * layer_stiffness * height * indentation**2
            for level in [0,1,2]:
                bary,w=rule(level)
                points=np.einsum('qv,fvc->fqc',bary,xf).reshape(-1,3)
                weights=(area[:,None]*w[None,:]).ravel()
                force=[]
                for xx in np.linspace(-.004,.004,501):
                    distance=np.linalg.norm(points-[xx,.004+height,0],axis=1)
                    normal_stress=layer_stiffness*np.maximum(radius-distance,0)
                    force.append(np.sum(weights*normal_stress*height/distance))
                force=np.array(force)
                rows.append({'cells':list(cells),'indentation_m':indentation,
                    'points_per_triangle':len(w),'exact_force_n':exact,
                    'relative_rms_error':float(np.sqrt(np.mean((force-exact)**2))/exact),
                    'force_peak_to_peak_over_exact':float(np.ptp(force)/exact),
                    'relative_mean_error':float(force.mean()/exact-1)})
    return {'schema':'static-contact-quadrature/1',
        'equation':'F_normal = pi * (E / skin_thickness) * h * (R-h)^2',
        'reference':'Exact integral of k*max(R-distance,0) times the vertical normal component over the full contact disk.',
        'setup':'Smooth translating 9 mm sphere over a flat fixed plane. E=60000 Pa, skin thickness=2 mm. No inertia, damping, friction, roughness or audio.',
        'limits':'An integration-error diagnosis, not a material or acoustic calibration.',
        'results':rows}

def dynamic_check(scratch: Path):
    from ku100sim.unified import SimulationEngine
    from scripts.make_hand_scenes import scene
    from scripts.validate_hand_scene import compare
    kernel=scratch/'native/solid/engine.cpp'; original=kernel.read_text()
    needle='for(int k=0;k<3;k++){V bary{1./6,1./6,1./6};bary[k]=2./3;points.push_back({ids,bary,A/3});}'
    if original.count(needle)!=1:
        raise RuntimeError('Kernel contact assembly changed; this research transform must be reviewed')
    replacement='''// Diagnostic uniform subdivision; unchanged force law.
   std::vector<std::array<V,3>> triangles{{V{1,0,0},V{0,1,0},V{0,0,1}}};
   for(int level=0;level<LEVEL;level++){
    std::vector<std::array<V,3>> next;
    for(const auto&t:triangles){V ab=mul(add(t[0],t[1]),.5),bc=mul(add(t[1],t[2]),.5),ca=mul(add(t[2],t[0]),.5);
     next.push_back({t[0],ab,ca});next.push_back({ab,t[1],bc});next.push_back({ca,bc,t[2]});next.push_back({ab,bc,ca});}
    triangles=std::move(next);
   }
   for(const auto&t:triangles)for(int k=0;k<3;k++){
    V bary{};for(int j=0;j<3;j++)bary=add(bary,mul(t[j],j==k?2./3:1./6));
    points.push_back({ids,bary,A/(3*triangles.size())});
   }'''
    rows={}; started=time.monotonic()
    try:
        for level in [0,1,2]:
            kernel.write_text(original if level==0 else original.replace(needle,replacement.replace('LEVEL',str(level))))
            for label,cells in [('default',[6,3,4]),('fine',[8,4,6])]:
                key=f'q{3*4**level}-{label}'; s=scene('light',cells=cells,duration=1.5,rate=96000)
                print('Running',key,flush=True)
                with SimulationEngine(s) as engine: result=engine.render()
                n=len(result['mesh']['rest'])+2; trace=result['trace']
                rows[key]={'time':trace[:,0], 'forces':trace[:,1+6*n:1+6*n+2],
                           'flux':result['flux'], 'report':result['report']}
                print('Completed',key,round(time.monotonic()-started,1),'s',flush=True)
    finally:
        kernel.write_text(original)
    comparisons={f'mesh_q{q}':compare(rows[f'q{q}-default'],rows[f'q{q}-fine'],96000,96000) for q in [3,12,48]}
    return {'schema':'contact-quadrature-development/1','production_kernel_unchanged':True,
      'scope':'Local scratch variants. No new production waveform or ASMR acceptance.',
      'trajectory':'Light-contact 1.5 s development case. The last knot is sampled from the five-second path, then the shortened knots are reinterpolated; this is NOT the exact first 1.5 s of the public render.',
      'same_material_force_law_and_trajectory_across_variants':True,'fitted_gain_or_time_alignment':False,
      'criteria':{'mesh_force_relative_l2':.05,'mesh_flux_relative_l2':.05},
      'comparisons':comparisons,
      'all_mesh_checks_passed':all(max(c['force_relative_l2'])<.05 and c['surface_flux_relative_l2']<.05 for c in comparisons.values()),
      'runs':{key:row['report'] for key,row in rows.items()},'human_listening_assessed':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--dynamic',action='store_true')
    a=p.parse_args(); repo=a.repo.resolve(); out=a.out.absolute()
    if out.is_symlink() or any(x.is_symlink() for x in out.parents):
        raise ValueError('Output must not contain symlinks')
    out.mkdir(parents=True,exist_ok=False)
    before=(repo/'native/solid/engine.cpp').read_bytes()
    if hashlib.sha256(before).hexdigest()!=EXPECTED_KERNEL:
        raise ValueError('This diagnostic is pinned to the first contact-scene kernel')
    with tempfile.TemporaryDirectory(prefix='ku100-contact-quadrature-') as d:
        scratch=Path(d)
        shutil.copytree(repo/'ku100sim',scratch/'ku100sim',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ['native/solid/engine.cpp','models/materials/ecoflex-compression.json','scripts/make_hand_scenes.py','scripts/validate_hand_scene.py']:
            dst=scratch/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,dst)
        sys.path.insert(0,str(scratch))
        from ku100sim.solid_scene import box_mesh
        report=static_check(box_mesh)
        (out/'static.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        if a.dynamic:
            report=dynamic_check(scratch)
            (out/'dynamic.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    assert (repo/'native/solid/engine.cpp').read_bytes()==before
    print(json.dumps({'out':str(out),'production_kernel_unchanged':True,'diagnosis_completed':True,'does_not_claim_quality_acceptance':True}))

if __name__=='__main__':main()
