"""One stateful renderer for declarative elastic/contact graphs.

All names are metadata. Native mechanics use SI-valued coordinates and shared
polynomial, spring, dashpot, relaxation and unilateral-contact elements.
This first reduced-coordinate engine is NOT an identified silicone, shell or
KU100 digital twin. Its readout is a weighted surface-velocity proxy, not Pa.
"""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import threading
import numpy as np
from scipy.linalg import expm
from scipy import signal

ROOT=Path(__file__).resolve().parents[1]
_LOCK=threading.Lock()
_SCHEMA='shared-mechanics/1'


def number(x,lo,hi,label):
    try: good=type(x) in (int,float) and math.isfinite(x) and lo<=x<=hi
    except OverflowError: good=False
    if not good: raise ValueError('Invalid '+label)
    return float(x)


def keys(x,allowed,label,required=()):
    if not isinstance(x,dict) or set(x)-set(allowed) or not set(required)<=set(x):
        raise ValueError('Invalid fields in '+label)


def curve(x,duration,label,limit):
    a=np.asarray(x,dtype=float)
    if (a.ndim!=2 or a.shape[1]!=2 or not 2<=len(a)<=256 or not np.isfinite(a).all()
        or a[0,0]!=0 or a[-1,0]!=duration or np.any(np.diff(a[:,0])<=0)
        or np.max(abs(a[:,1]))>limit):
        raise ValueError('Invalid '+label+' knots')
    return a


def interpolate(a,t):
    ix=np.minimum(np.searchsorted(a[:,0],t,side='right')-1,len(a)-2)
    ix=np.maximum(ix,0)
    z=np.clip((t-a[ix,0])/(a[ix+1,0]-a[ix,0]),0,1)
    z=z*z*z*(10+z*(-15+6*z))
    return a[ix,1]+z*(a[ix+1,1]-a[ix,1])


def validate_scene(scene):
    keys(scene,('schema','name','description','duration_s','internal_rate','nodes','couplings','evidence','microphone'),
         'scene',('schema','name','duration_s','nodes','evidence'))
    if scene['schema']!=_SCHEMA or not isinstance(scene['name'],str) or len(scene['name'])>160:
        raise ValueError('Invalid scene identity')
    evidence=scene['evidence']
    keys(evidence,('status','limits','sources','material_note'),'evidence',('status','limits'))
    if evidence['status'] not in ('unmeasured_reduced_model','numerical_test'):
        raise ValueError('No calibrated-material claim is implemented')
    if not isinstance(evidence['limits'],str) or len(evidence['limits'])>4000:raise ValueError('State model limits')
    duration=number(scene['duration_s'],.001,30,'duration')
    if 'microphone' in scene:
        from ku100sim.binaural import validate_microphone
        validate_microphone(scene['microphone'],duration)
    rate=scene.get('internal_rate',192000)
    if type(rate) is not int or rate not in (192000,384000,768000):raise ValueError('Invalid integration rate')
    if not isinstance(scene['nodes'],list) or not 1<=len(scene['nodes'])<=32:raise ValueError('Use 1–32 nodes')
    names=[];params=[];controls=[];weights=[]
    for node in scene['nodes']:
        keys(node,('id','mass_kg','k2_n_m','k4_n_m3','damping_n_s_m','memory','driver','initial','limit_m','readout_weight'),
             'node',('id','mass_kg','k2_n_m','limit_m'))
        name=node['id']
        if not isinstance(name,str) or not name or len(name)>80 or name in names:raise ValueError('Node IDs must be unique')
        names.append(name)
        m=number(node['mass_kg'],1e-10,100,'mass')
        k=number(node['k2_n_m'],-1e5,1e10,'linear stiffness')
        k4=number(node.get('k4_n_m3',0),0,1e18,'cubic stiffness')
        c=number(node.get('damping_n_s_m',0),0,1e5,'damping')
        limit=number(node['limit_m'],1e-7,.1,'coordinate limit')
        if k<0 and not k4>0:raise ValueError('Negative stiffness needs a bounded quartic potential')
        mem=node.get('memory',{});keys(mem,('stiffness_n_m','tau_s'),'memory')
        kr=number(mem.get('stiffness_n_m',0),0,1e9,'relaxation stiffness')
        tau=number(mem.get('tau_s',1),1e-4,100,'relaxation time')
        driver=node.get('driver',{});keys(driver,('stiffness_n_m','unilateral','displacement','force','travel','roughness'),'driver')
        kd=number(driver.get('stiffness_n_m',0),0,1e8,'drive stiffness')
        uni=driver.get('unilateral',False)
        if type(uni) is not bool:raise ValueError('Unilateral must be boolean')
        zero=[[0,0],[duration,0]]
        curves=[curve(driver.get(key,zero),duration,key,bound) for key,bound in [('displacement',.02),('force',10),('travel',1)]]
        rough=driver.get('roughness',[])
        if not isinstance(rough,list) or len(rough)>32:raise ValueError('Invalid surface profile')
        waves=[]
        max_speed=np.max(abs(np.diff(curves[2][:,1])/np.diff(curves[2][:,0])))*1.875
        for w in rough:
            keys(w,('amplitude_m','wavelength_m','phase_rad'),'roughness',('amplitude_m','wavelength_m'))
            amp=number(w['amplitude_m'],0,1e-3,'roughness amplitude')
            wavelength=number(w['wavelength_m'],1e-6,.1,'roughness wavelength')
            phase=number(w.get('phase_rad',0),-100,100,'roughness phase')
            if max_speed/wavelength>rate/32:raise ValueError('Unresolved surface-advection frequency')
            waves.append((amp,wavelength,phase))
        ini=node.get('initial',{});keys(ini,('q_m','v_m_s'),'initial')
        q=number(ini.get('q_m',0),-limit,limit,'initial displacement')
        v=number(ini.get('v_m_s',0),-10,10,'initial velocity')
        weights.append(number(node.get('readout_weight',1),-10,10,'readout weight'))
        params.append([m,k,k4,c,kr,tau,kd,float(uni),q,v,limit]);controls.append((curves,waves))
    p=np.asarray(params,dtype=np.float64);n=len(p);K=np.zeros((n,n))
    edges=scene.get('couplings',[])
    if not isinstance(edges,list) or len(edges)>128:raise ValueError('Too many couplings')
    for e in edges:
        keys(e,('a','b','stiffness_n_m'),'coupling',('a','b','stiffness_n_m'))
        if e['a'] not in names or e['b'] not in names or e['a']==e['b']:raise ValueError('Invalid endpoints')
        i,j=names.index(e['a']),names.index(e['b']);s=number(e['stiffness_n_m'],0,1e9,'coupling')
        K[i,i]+=s;K[j,j]+=s;K[i,j]-=s;K[j,i]-=s
    # Fail rather than silently integrating an arbitrarily stiff nonlinear graph.
    max_tangent=np.abs(p[:,1])+3*p[:,2]*p[:,10]**2+p[:,4]+p[:,6]+2*K.diagonal()
    if np.max(np.sqrt(max_tangent/p[:,0]))/rate>.65:raise ValueError('Graph exceeds integration-resolution envelope')
    if np.any(2*p[:,0]*rate**2+p[:,1]/2<=0):raise ValueError('Nonmonotone discrete step')
    exact=bool(not edges and not np.any(p[:,2]) and not np.any(p[:,4]) and not np.any(p[:,7]))
    return duration,rate,p,K,controls,np.asarray(weights),exact


def build_library():
    source=ROOT/'native/unified/engine.cpp'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    dest=ROOT/'build'/('unified-'+digest[:16]+'.so')
    with _LOCK:
        if not dest.exists():
            dest.parent.mkdir(exist_ok=True)
            temp=dest.with_suffix('.partial.so')
            subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Wpedantic','-fPIC','-shared',str(source),'-o',str(temp)],check=True)
            temp.replace(dest)
    lib=ct.CDLL(str(dest));D=ct.POINTER(ct.c_double)
    lib.unified_create.argtypes=[ct.c_int,ct.c_int,D,D,D,D,D,ct.c_int];lib.unified_create.restype=ct.c_void_p
    lib.unified_process.argtypes=[ct.c_void_p,ct.c_int,D,D,D];lib.unified_process.restype=ct.c_int
    lib.unified_destroy.argtypes=[ct.c_void_p];lib.unified_destroy.restype=None
    lib.unified_error.restype=ct.c_char_p
    return lib,digest


def ptr(a):return a.ctypes.data_as(ct.POINTER(ct.c_double))


class SimulationEngine:
    """A fresh instance per independent scene, continuous state across blocks.

    Metadata and object names never select the solver. Pure linear uncoupled
    graphs use an exact FOH optimization; all other supported graphs use the
    same discrete-gradient step. Controls are smooth kinematic/force curves.
    No recording, fitted sound buffer, or preset-name lookup enters rendering.
    """
    def __init__(self,scene):
        self._solid = None
        if isinstance(scene, dict) and scene.get("schema") == "coupled-solids/1":
            from .solid_scene import DeformableScene
            self._solid = DeformableScene(scene)
            return
        self.scene=json.loads(json.dumps(scene,allow_nan=False))
        self.duration,self.rate,self.params,self.K,self.controls,self.weights,self.exact=validate_scene(self.scene)
        self.n=len(self.params);self.frame=0;self.failed=False;self._handle=None
        self.lib,self.kernel_sha256=build_library()
        u,f=self.control_at(np.array([0.]))
        maps=np.zeros((self.n,4,4,4));h=1/self.rate
        if self.exact:
            fractions=[1,.5-np.sqrt(15)/10,.5,.5+np.sqrt(15)/10]
            for i,p in enumerate(self.params):
                A=np.zeros((4,4));A[0,1]=1;A[1,0]=-(p[1]+p[6])/p[0];A[1,1]=-p[3]/p[0];A[1,2]=1/p[0];A[2,3]=1
                for j,t in enumerate(fractions):maps[i,j]=expm(h*t*A)
        self._handle=self.lib.unified_create(self.n,self.rate,ptr(self.params),ptr(self.K),ptr(u),ptr(f),ptr(maps),int(self.exact))
        if not self._handle:raise RuntimeError(self.lib.unified_error().decode())
    def close(self):
        if getattr(self, "_solid", None) is not None:
            self._solid.close()
            return
        if getattr(self,"_handle",None):self.lib.unified_destroy(self._handle);self._handle=None
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()
    def __del__(self):self.close()
    def control_at(self,t):
        u=np.zeros((len(t),self.n));f=u.copy()
        for i,(curves,waves) in enumerate(self.controls):
            u[:,i]=interpolate(curves[0],t);f[:,i]=interpolate(curves[1],t)
            travel=interpolate(curves[2],t)
            for a,w,p in waves:u[:,i]+=a*np.sin(2*np.pi*travel/w+p)
        return u,f
    def process(self,frames,*,displacement=None,force=None,targets=None,target_velocities=None):
        if self._solid is not None:
            if displacement is not None or force is not None:
                raise ValueError("Solid scenes accept target positions/velocities, not scalar-node overrides")
            return self._solid.process(frames,targets=targets,target_velocities=target_velocities)
        if targets is not None or target_velocities is not None:
            raise ValueError("Scalar scenes have no geometric contact actors")
        if self.failed or not self._handle:raise RuntimeError('Engine closed or failed; create a new instance')
        if type(frames) is not int or not 1<=frames<=65536 or self.frame+frames>round(self.duration*self.rate):raise ValueError('Invalid block length')
        t=(self.frame+np.arange(1,frames+1))/self.rate;u,f=self.control_at(t)
        for value,dest,bound in [(displacement,u,.03),(force,f,10)]:
            if value is not None:
                a=np.asarray(value,dtype=np.float64)
                if a.shape!=dest.shape or not np.isfinite(a).all() or abs(a).max()>bound:raise ValueError('Invalid live controls')
                dest[:]=a
        out=np.empty((frames,3*self.n+4),dtype=np.float64)
        if self.lib.unified_process(self._handle,frames,ptr(u),ptr(f),ptr(out)):
            self.failed=True;raise RuntimeError(self.lib.unified_error().decode())
        self.frame+=frames
        return out
    def render_radiated(self, radiation):
        """Shared compact-array near-field research path for free modal ringing.

        Distinct from measured-only render_binaural(); predicted near-ear fields
        are explicitly uncalibrated. Unsupported nonlinear/contact scenes fail.
        """
        if self._solid is not None:raise ValueError('Free-ring radiation does not accept a deformable contact scene')
        from ku100sim.compact_radiation import render_radiated
        return render_radiated(self, radiation)

    def render_binaural(self,*,gain=12.,block_frames=2048):
        """Complete object-to-microphone output using the shared receiver."""
        if self._solid is not None:
            return self._solid.render_binaural(gain=gain,block_frames=block_frames)
        result=self.render(block_frames=block_frames)
        audio,receiver=preview_audio(result['velocity'],self.rate,gain,
            microphone=self.scene.get('microphone'),return_report=True)
        result['audio']=audio;result['report']['receiver']=receiver
        return result

    def render(self,*,block_frames=2048):
        if self._solid is not None:
            return self._solid.render(block_frames=block_frames)
        if self.frame:raise ValueError('render() requires fresh state; use process() to continue')
        if type(block_frames) is not int or not 1<=block_frames<=65536:raise ValueError('Invalid block size')
        frames=round(self.duration*self.rate);velocity=np.empty(frames);traces=[];stride=self.rate//240;max_balance=0.
        peak_q=np.zeros(self.n);crossings=np.zeros(self.n,dtype=int);oldsign=np.sign(self.params[:,8])
        for start in range(0,frames,block_frames):
            block=self.process(min(block_frames,frames-start))
            velocity[start:start+len(block)]=block[:,self.n:2*self.n]@self.weights
            peak_q=np.maximum(peak_q,np.max(abs(block[:,:self.n]),axis=0))
            signs=np.sign(block[:,:self.n]);all_signs=np.vstack([oldsign,signs]);crossings+=np.sum(all_signs[1:]*all_signs[:-1]<0,axis=0);oldsign=signs[-1]
            index=np.arange(start,start+len(block));sel=(index%stride)==0
            traces.append(np.column_stack([(index[sel]+1)/self.rate,block[sel]]))
            max_balance=max(max_balance,float(abs(block[:,-1]).max()))
        final=block[-1];energy0=float(final[-4]-final[-1]+final[-2]-final[-3])
        report={'schema':'shared-mechanics-result/1','engine':'SimulationEngine','kernel_sha256':self.kernel_sha256,
                'scene_sha256':hashlib.sha256(json.dumps(self.scene,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'sample_rate_internal':self.rate,'frames_internal':frames,'node_count':self.n,
                'integrator':'exact_linear_foh' if self.exact else 'discrete_gradient',
                'initial_energy_j':energy0,'final_energy_j':float(final[-4]),'input_work_j':float(final[-3]),
                'dissipation_j':float(final[-2]),'max_energy_balance_error_j':max_balance,
                'relative_balance_error':max_balance/max(abs(final[-3])+energy0,1e-16),
                'peak_coordinate_m':peak_q.tolist(),'zero_crossings':crossings.tolist(),
                'readout_domain':'weighted_surface_velocity_m_s','calibrated_microphone':False,
                'recording_input':False,'object_specific_solver_dispatch':False,'human_listening_assessed':False}
        return {'velocity':velocity,'trace':np.concatenate(traces),'report':report}


def _source_signal(velocity,rate,gain):
    """Explicit listening-only conversion; never label arbitrary digital gain Pa."""
    number(gain,0,1e7,'listening gain')
    taps,beta=signal.kaiserord(100,4000/(rate/2));taps+=taps%2==0
    fir=signal.firwin(taps,22000,fs=rate,window=('kaiser',beta))
    mono=signal.resample_poly(velocity,1,rate//48000,window=fir)
    mono=signal.sosfilt(signal.butter(2,35,fs=48000,btype='high',output='sos'),mono)*gain
    # Short end fade on the listening copy only; physical trace stays untouched.
    fade=min(480,len(mono)//4);mono[-fade:]*=.5+.5*np.cos(np.linspace(0,np.pi,fade))
    if not np.isfinite(mono).all() or abs(mono).max()>.8:raise ValueError('Preview overload; select an explicit smaller gain')
    return mono


def preview_audio(velocity,rate,gain,*,microphone=None,return_report=False):
    """Measured binaural listening render; never a duplicated-mono export.

    The internal weighted velocity remains an uncalibrated point-source proxy.
    This receiver does not manufacture source realism or contact-to-capsule data.
    """
    from ku100sim.binaural import BinauralMicrophone,default_microphone,require_binaural
    source=_source_signal(velocity,rate,gain);duration=len(source)/48000
    config=microphone if microphone is not None else default_microphone(duration)
    with BinauralMicrophone(config,duration,source_domain='weighted_surface_velocity_proxy') as mic:
        y,report=mic.render(source)
    if not np.isfinite(y).all() or abs(y).max()>.8:
        raise ValueError('Binaural preview overload; lower the explicit common source gain')
    audio=y.astype(np.float32)
    # A null mechanical test may legitimately have no sound. Publication requires
    # an excited source, two active channels, and a nonidentical measured response.
    if np.any(audio):require_binaural(audio)
    report['stereo']=__import__('ku100sim.binaural',fromlist=['stereo_metrics']).stereo_metrics(audio)
    return (audio,report) if return_report else audio
