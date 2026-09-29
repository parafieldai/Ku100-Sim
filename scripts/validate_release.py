#!/usr/bin/env python3
"""Independent continuous linear reference and bounded source-ablation receipts."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
import numpy as np
from scipy.linalg import expm
ROOT=Path(__file__).resolve().parents[1]
def main():
    rho,c,mu,V,r,l=1.204,343,1.81e-5,.8e-6,.0012,.002
    C=V/(rho*c*c);L=rho*l/(np.pi*r*r);R=8*mu*(l+.0001)/(np.pi*r**4);rr=rho*c/(4*np.pi*r*r);tau=r/c
    A=np.array([[0,-1/C,0],[1/L,-(R+rr)/L,rr/L],[0,1/tau,-1/tau]])
    exact=expm(A*.002)@np.array([80.,0,0]);weights=np.sqrt([C,L,rr*tau]);errors=[];cases={}
    with tempfile.TemporaryDirectory() as d:
        folder=Path(d);binary=folder/'probe';subprocess.run(['g++','-std=c++17','-O3','-I',str(ROOT/'native'),str(ROOT/'tests/release_probe.cpp'),'-o',str(binary)],check=True)
        for rate in [192000,384000,768000]:
            v=np.fromstring(subprocess.check_output([str(binary),'linear',str(rate)],text=True),sep=' ')
            relative=float(np.linalg.norm((v[:3]-exact)*weights)/np.linalg.norm(exact*weights));errors.append({'rate_hz':rate,'energy_weighted_state_relative_error':relative,'passes_0_5_percent':relative<=.005,'energy_residual_j':float(v[3])})
        signals={}
        for mode,rate in [('sealed',384000),('sealed',768000),('vented',768000),('slow',768000),('silence',768000)]:
            name=f'{mode}-{rate}';path=folder/(name+'.f64');v=np.fromstring(subprocess.check_output([str(binary),mode,str(rate),str(path)],text=True),sep=' ')
            x=np.fromfile(path,dtype=np.float64);signals[name]=x
            cases[name]=dict(zip(['max_energy_residual_j','work_j','loss_j','final_energy_j','max_pressure_pa','max_mach','max_reynolds'],map(float,v)))
            cases[name]['waveform_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();cases[name]['source_rms_pa']=float(np.sqrt(np.mean(x*x)))
        fine=signals['sealed-768000'];coarse=signals['sealed-384000'];refinement=float(np.linalg.norm(coarse-fine[1::2])/np.linalg.norm(fine[1::2]))
        assert errors[-1]['passes_0_5_percent'] and refinement<.005
        assert np.all(signals['silence-768000']==0)
    report={'schema':'pressure-release-validation/1','linear_reference':'Independent continuous 3x3 matrix exponential, constant open aperture, legacy viscosity, no nonlinear entrance loss; not a reference for the entire nonlinear switched model',
        'linear_duration_s':.002,'linear_initial_state':[80.,0.,0.],'relative_tolerance':.005,'linear_refinement':errors,
        'source_cases':cases,'nonlinear_unsteady_refinement_384_to_768_khz':refinement,'reference_time_alignment':'End-of-step times; no fitted gain, delay or phase',
        'vented_to_sealed_rms_ratio':cases['vented-768000']['source_rms_pa']/cases['sealed-768000']['source_rms_pa'],
        'silence_exact':True,'numerical_checks_passed':True,'target_mechanism_identified':False,'wet_contact_fidelity_established':False,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'native/release.hpp',ROOT/'tests/release_probe.cpp',Path(__file__)]}}
    dest=ROOT/'validation/local/release-validation.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
