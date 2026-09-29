"""Rigid-sphere Helmholtz benchmark, not an anatomical KU100 model.
Outgoing exp(+ikr) convention; returns normalized frequency responses.
Duda & Martens (1998), DOI 10.1121/1.423886. No fitted microphone parameters.
"""
from __future__ import annotations
import argparse,json,pathlib
import numpy as np
from scipy.special import spherical_jn,spherical_yn,eval_legendre

def transfer(frequency,cos_theta,radius=.0875,distance=.25,extra_terms=0):
    f=np.atleast_1d(np.asarray(frequency,float));theta=np.atleast_1d(np.asarray(cos_theta,float))
    if not np.isfinite(f).all() or np.any(f<=0) or np.any(abs(theta)>1) or not np.isfinite(theta).all() or not 0<radius<distance:
        raise ValueError('Finite positive frequency, valid angle, and source outside sphere required')
    result=np.empty((len(f),len(theta)),complex)
    for i,hz in enumerate(f):
        k=2*np.pi*hz/343;z=k*radius;zs=k*distance
        N=int(np.ceil(z+4*np.cbrt(z)+18))+extra_terms;n=np.arange(N+1)
        out=spherical_jn(n,zs)+1j*spherical_yn(n,zs)
        deriv=spherical_jn(n,z,True)+1j*spherical_yn(n,z,True)
        weights=(2*n+1)*out/deriv
        result[i]=-distance/(k*radius**2)*np.exp(-1j*zs)*(weights[:,None]*eval_legendre(n[:,None],theta[None,:])).sum(axis=0)
    if not np.isfinite(result).all():raise FloatingPointError('Spherical series did not evaluate finitely')
    return result

def benchmark():
    f=np.geomspace(100,8000,90);theta=np.cos(np.deg2rad([0,45,90,135,180]))
    a=transfer(f,theta);b=transfer(f,theta,extra_terms=12)
    convergence=float(np.max(abs(a-b)/np.maximum(abs(b),1e-15)))
    far=transfer([1.0],[1,0,-1],distance=100.)
    dc=np.array([sum((2*n+1)/(n+1)*(.0875/.25)**n*eval_legendre(n,t) for n in range(150)) for t in [1,0,-1]])
    near=transfer([.1],[1,0,-1])[0]
    low_error=float(np.max(abs(abs(near)-dc)))
    return {'series_relative_error':convergence,'far_field_low_frequency_magnitude':abs(far[0]).tolist(),'static_limit_max_magnitude_error':low_error,'passed':bool(convergence<1e-8 and low_error<1e-5 and np.max(abs(abs(far)-1))<.01),'scope':'Series convergence and static limits only; the ideal sphere has no pinnae and does not establish contact fidelity.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=pathlib.Path,default=pathlib.Path('research/sphere.json'));a=p.parse_args();r=benchmark();a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if r['passed'] else 1)
