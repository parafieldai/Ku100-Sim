"""Executable verification, not a claim of calibrated wet-ear realism."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.linalg import expm

ROOT=pathlib.Path(__file__).resolve().parents[1]

def linear_reference(seconds: float, os: int, force: float=0.0):
    # Independent continuous-state assembly; no native coefficient/state files read.
    rho,c=1.204,343.; lx,ly,h,E,nu,rhos=.03,.04,.001,1.2e6,.49,1100.
    area=4*lx*ly/np.pi**2; mass=rhos*h*lx*ly/4
    bend=E*h**3/(12*(1-nu**2)); kk=(np.pi/lx)**2+(np.pi/ly)**2
    k=mass*bend*kk**2/(rhos*h); damp=.08*np.sqrt(k*mass)
    C=1e-6/(rho*c*c); a=.0015
    M=rho*.01/(np.pi*a*a); R=8*1.81e-5*.01/(np.pi*a**4)
    Rr=rho*c/(4*np.pi*a*a); tau=a/c
    # qL,qR,vL,vR,pL,pR,UL,UR,hL,hR; spring coefficient 1 N/m.
    A=np.zeros((10,10)); A[0,2]=A[1,3]=1
    s=np.array([area/(lx*ly),-area/(lx*ly)])
    A[2:4,:2]=-(np.eye(2)*k+np.outer(s,s))/mass
    A[2:4,2:4]=-np.eye(2)*damp/mass
    for e in range(2):
        A[2+e,4+e]=-area/mass
        A[4+e,2+e]=area/C; A[4+e,6+e]=-1/C
        A[6+e,4+e]=1/M; A[6+e,6+e]=-(R+Rr)/M; A[6+e,8+e]=Rr/M
        A[8+e,6+e]=1/tau; A[8+e,8+e]=-1/tau
    y=np.zeros(11); y[2]=.001; y[10]=1
    B=np.zeros((11,11)); B[:10,:10]=A
    shape=np.sin(np.pi*.47)*np.exp(-.5*.0015**2*kk)
    B[2,10]=force*shape/mass
    T=round((seconds+.2)*48000*os)/(48000*os)
    expected=(expm(B*T)@y)[:10]
    energy=np.zeros((10,10)); energy[:2,:2]=np.eye(2)*k+np.outer(s,s)
    energy[2:4,2:4]=np.eye(2)*mass
    energy[4:6,4:6]=np.eye(2)*C;energy[6:8,6:8]=np.eye(2)*M;energy[8:10,8:10]=np.eye(2)*Rr*tau
    return expected,energy

def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',default=str(ROOT/'build/ku100_sim'));p.add_argument('--report',default=str(ROOT/'research/verification.json'));a=p.parse_args()
    exe=str(pathlib.Path(a.exe).resolve()); rows=[]
    def check(name,ok,**detail):
        rows.append(dict(name=name,passed=bool(ok),**detail));print(('PASS ' if ok else 'FAIL ')+name,flush=True)
    with tempfile.TemporaryDirectory(prefix='ku100-audit-') as td:
        base=pathlib.Path(td)
        def render(name,args):
            out=base/name
            proc=subprocess.run([exe,'--out',str(out),*args],capture_output=True,text=True,timeout=120)
            if proc.returncode:raise RuntimeError(proc.stderr)
            x,fs=sf.read(out/'audio.wav',always_2d=True)
            return json.loads((out/'manifest.json').read_text()),x,out
        jobs={
          'silence':['--seconds','.04','--modes','2','--action','silence'],
          'left':['--seconds','.2','--modes','4'],
          'replay':['--seconds','.2','--modes','4'],
          'right':['--seconds','.2','--modes','4','--side','right'],
          'uncoupled':['--seconds','.2','--modes','4','--coupling','0'],
          'dry':['--seconds','.2','--modes','4','--viscosity','0'],
          'time4':['--seconds','.2','--modes','4','--oversample','4'],
          'time16':['--seconds','.2','--modes','4','--oversample','16'],
          'space6':['--seconds','.2','--modes','6'],
          'space8':['--seconds','.2','--modes','8'],
          'space12':['--seconds','.2','--modes','12'],
          'linear4':['--seconds','.01','--modes','1','--action','linear','--initial-velocity','.001','--oversample','4'],
          'linear8':['--seconds','.01','--modes','1','--action','linear','--initial-velocity','.001','--oversample','8'],
          'linear64':['--seconds','.01','--modes','1','--action','linear','--initial-velocity','.001','--oversample','64'],
          'linear16':['--seconds','.01','--modes','1','--action','linear','--initial-velocity','.001','--oversample','16'],
          'forced':['--seconds','.01','--modes','1','--action','linear','--initial-velocity','.001','--force','.0001'],
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures={n:pool.submit(render,n,v) for n,v in jobs.items()}
            data={n:f.result() for n,f in futures.items()}
        for name,(m,x,o) in data.items():
            check(name+': finite stereo export',x.shape==(m['frames'],2) and np.isfinite(x).all())
            check(name+': work-energy balance',m['relative_energy_residual']<1e-7,residual=m['relative_energy_residual'])
            check(name+': nonnegative dissipations',all(m[k]>=0 for k in ['solid_loss_j','film_loss_j','vent_loss_j','radiation_loss_j']))
        check('zero state and no drive produce exact silence',np.count_nonzero(data['silence'][1])==0)
        check('deterministic WAV bytes', (data['left'][2]/'audio.wav').read_bytes()==(data['replay'][2]/'audio.wav').read_bytes())
        check('API side mirror (implemented channel swap)',np.array_equal(data['left'][1],data['right'][1][:,::-1]))
        check('zero coupling isolates opposite cavity',np.count_nonzero(data['uncoupled'][1][:,1])==0)
        check('viscosity has a nonzero physical effect',not np.array_equal(data['left'][1],data['dry'][1]))
        errors=[]
        for os in [4,8,16]:
            expected,H=linear_reference(.01,os); got=np.array(data['linear'+str(os)][0]['final_state']);err=got-expected
            rel=float(np.sqrt(err@H@err/(expected@H@expected))); errors.append(rel)
            # Lower-rate failures are retained as accuracy diagnostics, not relabeled as passes.
        expected,H=linear_reference(.01,64);err=np.array(data['linear64'][0]['final_state'])-expected
        high_error=float(np.sqrt(err@H@err/(expected@H@expected)))
        check('reference-quality OS64 linear ODE error below 0.5 percent',high_error<.005,energy_norm_relative_error=high_error)
        check('linear refinement is second order',all(3.5<errors[i]/errors[i+1]<4.5 for i in [0,1]),error_ratios=[errors[i]/errors[i+1] for i in [0,1]])
        expected,H=linear_reference(.01,8,.0001);err=np.array(data['forced'][0]['final_state'])-expected
        rel=float(np.sqrt(err@H@err/(expected@H@expected)))
        check('forced linear ODE independent reference',rel<.005,energy_norm_relative_error=rel)
        # Diagnostics are observations, not acceptance gates selected after the result.
        diagnostics={'linear_error':errors,'lower_rates_meet_0_5_percent_target':[v<.005 for v in errors],'OS64_linear_error':high_error,'native_input_domain':'assumed plate/cavity surrogate','nonlinear_refinement':{},'spatial_refinement':{},'runs':{n:{k:v for k,v in m.items() if k!='final_state'} for n,(m,_,_) in data.items()}}
        for n in ['time4','left']:
            x=data[n][1];y=data['time16'][1];N=min(len(x),len(y))
            diagnostics['nonlinear_refinement'][n]=float(np.linalg.norm(x[:N]-y[:N])/np.linalg.norm(y[:N]))
        for n in ['left','space6','space8']:
            x=data[n][1];y=data['space12'][1]
            diagnostics['spatial_refinement'][n]=float(np.linalg.norm(x-y)/np.linalg.norm(y))
        invalid=[['--seconds','nan'],['--seconds','-1'],['--unknown','3'],['--modes','2.5'],['--oversample','5'],['--side','both'],['--seconds','15','--oversample','512','--modes','24'],['--filter-gain','2'],['--receiver','measured'],['--seconds','.02','--seconds','.03']]
        for i,args in enumerate(invalid):
            r=subprocess.run([exe,'--out',str(base/f'bad{i}'),*args],capture_output=True,timeout=10)
            check('reject invalid input '+str(i),r.returncode!=0 and not (base/f'bad{i}').exists())
        r=subprocess.run([exe,'--out',str(data['left'][2])],capture_output=True,timeout=10)
        check('refuse overwrite',r.returncode!=0)
    report={'checks':rows,'passed':all(r['passed'] for r in rows),'count':len(rows),'diagnostics':diagnostics,'source_sha256':hashlib.sha256((ROOT/'src/sim.cpp').read_bytes()).hexdigest(),'limits':'No independent subagent or human listening review. Linear oracle is a separately assembled implementation, not experimental contact data.'}
    dest=pathlib.Path(a.report);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
