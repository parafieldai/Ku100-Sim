#!/usr/bin/env python3
"""Read the actual author's ZIP; fit a bounded nominal-compression approximation.

This does not estimate acoustic damping, human friction, or multiaxial truth.
File numbers 1-3 fit; 4-5 are fixed development checks, not blind listening data.
"""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def fit(raw):
    if hashlib.sha256(raw).hexdigest()!='7acde7e17883150264a528a55bced8d1828c8f70179066df81ad4f6545c5b856':raise ValueError('Wrong published ZIP')
    sources=[];arrays=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for i in range(1,6):
            n=f'Uniaxial compression/Ecoflex 00-30 - {i}.csv';b=z.read(n)
            if b.splitlines()[0]!=b'Strain (%),Stress (MPa)':raise ValueError('Unexpected units')
            data=np.genfromtxt(io.BytesIO(b),delimiter=',',skip_header=1);strain=data[:,0]/100;stress=data[:,1]*1e6
            mask=(strain>=.05)&(strain<=.20);l=1-strain[mask];g=l**-2-l;y=stress[mask];arrays.append((g,y))
            sources.append({'path':n,'sha256':hashlib.sha256(b).hexdigest(),'rows':len(data),'fit_rows':int(mask.sum()),'split':'fit' if i<=3 else 'development-evaluation'})
    gx=np.concatenate([g for g,y in arrays[:3]]);gy=np.concatenate([y for g,y in arrays[:3]])
    mu=float(gx@gy/(gx@gx))
    for r,(g,y) in zip(sources,arrays):r['stress_relative_l2']=float(np.linalg.norm(mu*g-y)/np.linalg.norm(y))
    return {'schema':'silicone-compression-fit/1','formulation':'Ecoflex 00-30','mu_pa':mu,'fitting_domain':'5-20 percent reported nominal compression','model':'ideal homogeneous incompressible neo-Hookean nominal stress mu*(lambda^-2-lambda)',
      'offset_fit':False,'source':'https://zenodo.org/records/14983287','archive_sha256':hashlib.sha256(raw).hexdigest(),'source_files':sources,
      'caveats':['Specimen/fixture friction and crosshead processing are not separately identified','Not an Ogden parameter recovery or multiaxial validation','Dynamic damping, bulk modulus, finger parameters and skin/silicone friction are not identified here','No microphone or audio data present; does not establish an ASMR sound'],'production_material_calibrated':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip',type=Path);p.add_argument('--out',type=Path,default=ROOT/'models/materials/ecoflex-compression.json');a=p.parse_args();r=fit(a.zip.read_bytes());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
