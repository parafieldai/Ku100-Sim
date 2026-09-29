#!/usr/bin/env python3
"""Verify native tube coefficients against the independent circular Bessel solution.

The frequency response check concerns the continuous rational model. Separate
step-refinement tests qualify its midpoint discretization in a coupled scene.
No acoustic recording or data-driven fit is used by this calculation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from scipy.special import ive
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('viscous_tests',ROOT/'tests/test_viscous.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def validate():
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder);(p/'probe.cpp').write_text(module.PROBE)
        subprocess.run(['g++','-std=c++17','-O2','-I',str(ROOT/'native'),str(p/'probe.cpp'),'-o',str(p/'probe')],check=True)
        rows=[]
        for radius in [.0005,.001,.003,.01]:
            result=json.loads(subprocess.check_output([str(p/'probe'),str(radius),'192000'],text=True))
            frequencies=np.geomspace(20,20000,1001);s=2j*np.pi*frequencies
            z=radius*np.sqrt(s*1.204/1.81e-5);mass=1.204*.18/(np.pi*radius**2)
            exact=mass*s*ive(0,z)/ive(2,z)
            approx=result['mass']*s+result['r0']+sum(w*s/(s+l) for w,l in zip(result['weights'],result['poles']))
            legacy=mass*s+result['r0']
            row={'radius_m':radius,'max_complex_relative_error':float(np.max(abs(approx-exact)/abs(exact))),
                 'max_resistance_relative_error':float(np.max(abs(approx.real-exact.real)/exact.real)),
                 'legacy_max_resistance_relative_error':float(np.max(abs(legacy.real-exact.real)/exact.real)),
                 'legacy_max_complex_relative_error':float(np.max(abs(legacy-exact)/abs(exact))),
                 'low_frequency_inertance_ratio':(result['mass']+sum(w/l for w,l in zip(result['weights'],result['poles'])))/mass,
                 'discrete_relative_work_residual':result['max_residual']/abs(result['work'])}
            if row['max_complex_relative_error']>=.0003 or row['max_resistance_relative_error']>=.004 or row['discrete_relative_work_residual']>=1e-10:raise AssertionError(row)
            rows.append(row)
    return {'schema':'viscous-tube-validation/1','generated_utc':datetime.now(timezone.utc).isoformat(),
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'native/viscous.hpp',ROOT/'tests/test_viscous.py',Path(__file__)]},
            'reference':'Z(s) = rho*length/A * s * I0(radius*sqrt(s/nu))/I2(radius*sqrt(s/nu))',
            'grid':{'frequency_hz':[20,20000],'points_per_radius':1001,'density_kg_m3':1.204,'viscosity_pa_s':1.81e-5,'length_m':.18},
            'rows':rows,'passed':True,'thermal_losses_modeled':False,'ku100_or_wet_contact_calibrated':False,
            'limits':['Circular, rigid, laminar no-slip tube model; not a KU100 geometry claim','Continuous rational impedance error excludes timestep and mesh error','Coefficient approximation verified only over declared radii and frequency grid','Time-varying geometry, thermal admittance, turbulent flow and liquid free surfaces remain outside this model']}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'validation/local/viscous-validation.json');args=ap.parse_args()
    report=validate();args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2))
