"""Shared finite-deformation scene backend; fingertip proxies are not a whole hand.

The object is a connected tetrahedral solid. Contact and actuator reaction are
integrated with it, not driven by recorded sound. Acoustic output is separate.
"""
from __future__ import annotations
import ctypes as ct
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import threading
import time
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1]
_LOCK=threading.Lock()

def num(x,lo,hi,label):
    try:ok=type(x) in (int,float) and math.isfinite(x) and lo<=x<=hi
    except OverflowError:ok=False
    if not ok:raise ValueError('Invalid '+label)
    return float(x)

def fields(obj,allowed,required,label):
    if not isinstance(obj,dict) or set(obj)-set(allowed) or set(required)-set(obj):raise ValueError('Invalid fields in '+label)

def box_mesh(size,cells):
    """Conforming six-tetrahedra Freudenthal split of each rectangular grid cell."""
    size=np.asarray(size,float)
    if size.shape!=(3,) or not np.isfinite(size).all() or np.any(size<=0):raise ValueError('Positive box size')
    if len(cells)!=3 or any(type(n) is not int or not 1<=n<=16 for n in cells):raise ValueError('Bounded cell counts')
    axes=[np.linspace(-s/2,s/2,n+1) for s,n in zip(size,cells)]
    shape=tuple(n+1 for n in cells)
    xyz=np.array(list(itertools.product(*axes)),dtype=float)
    idx=lambda q:np.ravel_multi_index(tuple(q),shape)
    tets=[]
    for base in itertools.product(*(range(n) for n in cells)):
        for perm in itertools.permutations(range(3)):
            p=np.array(base);ids=[idx(p)]
            for d in perm:p[d]+=1;ids.append(idx(p))
            if np.linalg.det((xyz[ids[1:]]-xyz[ids[0]]).T)<0:ids[1],ids[2]=ids[2],ids[1]
            tets.append(ids)
    counts={}
    for tet in tets:
        for omitted in range(4):
            ids=[tet[k] for k in range(4) if k!=omitted];key=tuple(sorted(ids))
            if key in counts:counts[key]=None;continue
            a,b,c=xyz[ids];n=np.cross(b-a,c-a)
            if np.dot(n,xyz[tet[omitted]]-a)>0:ids[1],ids[2]=ids[2],ids[1]
            counts[key]=ids
    faces=np.array([v for v in counts.values() if v is not None],np.int32)
    av=.5*np.cross(xyz[faces[:,1]]-xyz[faces[:,0]],xyz[faces[:,2]]-xyz[faces[:,0]])
    a=np.linalg.norm(av,axis=1);areas=np.zeros(len(xyz))
    for i in range(3):np.add.at(areas,faces[:,i],a/3)
    group=2*np.argmax(abs(av),axis=1)+(np.sum(av,axis=1)<0)
    return xyz,np.array(tets,np.int32),faces,areas,group.astype(np.int32)

def build_library():
    p=ROOT/'native/solid/engine.cpp';h=hashlib.sha256(p.read_bytes()).hexdigest();dest=ROOT/'build'/('solid-'+h[:16]+'.so')
    with _LOCK:
        if not dest.exists():
            dest.parent.mkdir(exist_ok=True);tmp=dest.with_suffix('.partial.so')
            subprocess.run(['g++','-std=c++17','-O3','-fPIC','-shared','-Wall','-Wextra',str(p),'-o',str(tmp)],check=True);tmp.replace(dest)
    lib=ct.CDLL(str(dest));D=ct.POINTER(ct.c_double);I=ct.POINTER(ct.c_int)
    lib.solid_create.argtypes=[ct.c_int,ct.c_int,ct.c_int,ct.c_double,D,I,I,D,D,ct.c_double,D,D,ct.c_int,I,ct.c_int];lib.solid_create.restype=ct.c_void_p
    lib.solid_process.argtypes=[ct.c_void_p,ct.c_int,D,D,D];lib.solid_process.restype=ct.c_int
    lib.solid_destroy.argtypes=[ct.c_void_p];lib.solid_destroy.restype=None;lib.solid_error.restype=ct.c_char_p
    lib.solid_material.argtypes=[D,D,D,D];lib.solid_material.restype=ct.c_int
    lib.solid_volume_probe.argtypes=[ct.c_int,ct.c_int,I,D,D,ct.c_double,D];lib.solid_volume_probe.restype=ct.c_int
    return lib,h

def ptr(a):return a.ctypes.data_as(ct.POINTER(ct.c_double))
def iptr(a):return a.ctypes.data_as(ct.POINTER(ct.c_int))

def trajectory(knots,t):
    """C2 pose and matching analytic velocity; no finite-difference drive spikes."""
    a=np.asarray(knots,float);t=np.asarray(t,float)
    j=np.clip(np.searchsorted(a[:,0],t,side='right')-1,0,len(a)-2)
    dt=a[j+1,0]-a[j,0];s=np.clip((t-a[j,0])/dt,0,1)
    p=s**3*(10+s*(-15+6*s));v=30*s**2*(1-s)**2/dt
    diff=a[j+1,1:]-a[j,1:]
    return a[j,1:]+p[:,None]*diff,v[:,None]*diff

def validate(scene):
    fields(scene,['schema','name','duration_s','internal_rate','solid','fingertips','microphone','evidence'],['schema','name','duration_s','solid','fingertips','microphone','evidence'],'scene')
    if scene['schema']!='coupled-solids/1':raise ValueError('Wrong scene schema')
    if not isinstance(scene['name'],str) or len(scene['name'])>160:raise ValueError('Invalid name')
    duration=num(scene['duration_s'],.001,12,'duration');rate=scene.get('internal_rate',96000)
    if type(rate) is not int or rate not in (48000,96000,192000):raise ValueError('Invalid rate')
    solid=scene['solid'];fields(solid,['geometry','material','support','volume_formulation'],['geometry','material','support'],'solid')
    if solid.get('volume_formulation','element') not in ('element','averaged_nodal'):raise ValueError('Unsupported volume formulation')
    geo=solid['geometry'];fields(geo,['type','size_m','cells'],['type','size_m','cells'],'geometry')
    if geo['type']!='tetrahedral_box':raise ValueError('Unsupported geometry; no solid/fluid fallback')
    size=[num(x,.001,.15,'size') for x in geo['size_m']]
    if len(size)!=3:raise ValueError('3D geometry required')
    xyz,tets,faces,area,groups=box_mesh(size,geo['cells'])
    if len(xyz)>1500 or len(tets)>6000:raise ValueError('Scene exceeds budget')
    m=solid['material'];allowed=['name','density_kg_m3','mu_pa','bulk_pa','shear_viscosity_pa_s','bulk_viscosity_pa_s','memory','provenance']
    fields(m,allowed,allowed,'material')
    rho=num(m['density_kg_m3'],500,2000,'density');mu=num(m['mu_pa'],1000,1e6,'shear modulus');bulk=num(m['bulk_pa'],1e4,1e8,'bulk modulus')
    eta=num(m['shear_viscosity_pa_s'],0,5,'viscosity');etav=num(m['bulk_viscosity_pa_s'],0,5,'bulk viscosity')
    memory=m['memory']
    if not isinstance(memory,list) or len(memory)!=2:raise ValueError('Two explicit relaxation branches required')
    mat=[mu,bulk,eta,etav]
    for b in memory:
        fields(b,['mu_pa','tau_s'],['mu_pa','tau_s'],'memory');mat += [num(b['mu_pa'],0,1e5,'memory modulus'),num(b['tau_s'],.001,1e5,'memory time')]
    # Conservative geometric resolution envelope; separate mesh/time tests remain mandatory.
    cell=np.min(np.array(size)/np.array(geo['cells']))
    if math.sqrt((bulk+4*(mu+mat[4]+mat[6])/3)/rho)/rate/cell>.25:raise ValueError('Time step under-resolves elastic waves')
    if 2*max(eta,etav)/rho/cell**2/rate>.1:raise ValueError('Viscous explicit step too large')
    support=solid['support']
    if support not in ('clamped_x_min','free'):raise ValueError('Unsupported support')
    fixed=np.asarray(np.isclose(xyz[:,0],-size[0]/2,atol=1e-12)&(support=='clamped_x_min'),dtype=np.int32)
    actors=scene['fingertips'];params=[];curves=[]
    if not isinstance(actors,list) or not 1<=len(actors)<=4:raise ValueError('1-4 contacting actors')
    required=['id','mass_kg','radius_m','drive_stiffness_n_m','drive_damping_n_s_m','skin_modulus_pa','skin_layer_m','normal_viscosity_pa_s_m','tangential_stiffness_pa_m','mu_static','mu_dynamic','stribeck_speed_m_s','target_knots','provenance']
    names=[]
    for a in actors:
        fields(a,required,required,'fingertip')
        if not isinstance(a['id'],str) or a['id'] in names:raise ValueError('Unique actor identity');
        names.append(a['id'])
        mass=num(a['mass_kg'],.001,.2,'actor mass');r=num(a['radius_m'],.003,.025,'tip radius')
        kd=num(a['drive_stiffness_n_m'],10,1e5,'drive stiffness');cd=num(a['drive_damping_n_s_m'],0,100,'drive damping')
        kn=num(a['skin_modulus_pa'],1e3,1e6,'skin modulus')/num(a['skin_layer_m'],.0002,.005,'skin layer')
        cn=num(a['normal_viscosity_pa_s_m'],0,1e4,'normal viscosity');kt=num(a['tangential_stiffness_pa_m'],0,1e9,'tangential stiffness')
        mus=num(a['mu_static'],0,2,'static friction');mud=num(a['mu_dynamic'],0,mus,'dynamic friction');vs=num(a['stribeck_speed_m_s'],1e-5,.1,'transition speed')
        params.append([mass,r,kd,cd,kn,cn,kt,mus,mud,vs])
        knots=np.asarray(a['target_knots'],float)
        if knots.ndim!=2 or knots.shape[1]!=4 or not 2<=len(knots)<=64 or not np.isfinite(knots).all() or knots[0,0]!=0 or knots[-1,0]!=duration or np.any(np.diff(knots[:,0])<=0) or abs(knots[:,1:]).max()>.2:raise ValueError('Invalid target knots')
        if np.max(np.linalg.norm(np.diff(knots[:,1:],axis=0),axis=1)/np.diff(knots[:,0]))*1.875>.25:raise ValueError('Driver too fast')
        if np.min(np.linalg.norm(xyz-knots[0,1:],axis=1))<r:raise ValueError('Start with separated fingertip geometry')
        curves.append(knots)
    cap=scene['microphone']
    fields(cap,['model','radius_m','azimuth_deg'],['model','radius_m','azimuth_deg'],'microphone')
    if cap['model']!='KU100_NF':raise ValueError('Only measured KU100 bank supported')
    if num(cap['radius_m'],.25,1.5,'microphone radius') not in (.25,.5,.75,1.,1.5):raise ValueError('No unmeasured range extrapolation')
    num(cap['azimuth_deg'],-180,180,'azimuth')
    if not isinstance(scene['evidence'],dict) or scene['evidence'].get('status')!='research_prototype':raise ValueError('Explicit prototype status required')
    return duration,rate,xyz,tets,faces,area,groups,fixed,np.array(mat),rho,np.array(params),curves

class DeformableScene:
    """Backend composed by SimulationEngine, selected by scene schema, not object name."""
    def __init__(self,scene):
        self._handle=None;self.failed=False;self.scene=json.loads(json.dumps(scene,allow_nan=False));self.frame=0
        (self.duration,self.rate,self.rest,self.tets,self.faces,self.area,self.groups,self.fixed,self.mat,self.rho,self.params,self.curves)=validate(self.scene)
        self.n=len(self.rest);self.na=len(self.params);self.lib,self.kernel_sha256=build_library()
        target,_=self.control_at(np.array([0.]));self.dim=6*(self.n+self.na)+2*self.na+7
        self._handle=self.lib.solid_create(self.n,len(self.tets),self.na,1/self.rate,ptr(self.rest),iptr(self.tets),iptr(self.fixed),ptr(self.area),ptr(self.mat),self.rho,ptr(self.params),ptr(target),len(self.faces),iptr(self.faces),int(self.scene['solid'].get('volume_formulation','element')=='averaged_nodal'))
        if not self._handle:raise RuntimeError(self.lib.solid_error().decode())
    def close(self):
        if self._handle:self.lib.solid_destroy(self._handle);self._handle=None
    def __del__(self):self.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def control_at(self,t):
        pairs=[trajectory(k,t) for k in self.curves]
        return np.ascontiguousarray(np.stack([p for p,v in pairs],axis=1)),np.ascontiguousarray(np.stack([v for p,v in pairs],axis=1))
    def process(self,frames,*,targets=None,target_velocities=None):
        if self.failed or not self._handle:raise RuntimeError('Closed or failed engine')
        if type(frames) is not int or not 1<=frames<=8192 or self.frame+frames>round(self.duration*self.rate):raise ValueError('Invalid frames')
        t=(self.frame+np.arange(1,frames+1))/self.rate;p,v=self.control_at(t)
        if targets is not None:
            if target_velocities is None:raise ValueError('Live targets require matching velocities')
            for src,dst,bound in [(targets,p,.2),(target_velocities,v,.25)]:
                a=np.asarray(src,float)
                if a.shape!=dst.shape or not np.isfinite(a).all() or abs(a).max()>bound:raise ValueError('Invalid live targets')
                dst[:]=a
        elif target_velocities is not None:raise ValueError('Velocity needs position')
        out=np.empty((frames,self.dim))
        if self.lib.solid_process(self._handle,frames,ptr(p),ptr(v),ptr(out)):
            self.failed=True;raise RuntimeError(self.lib.solid_error().decode())
        self.frame+=frames;return out
    def render(self,*,block_frames=512):
        if self.frame:raise ValueError('Fresh engine required')
        if type(block_frames) is not int or not 1<=block_frames<=8192:raise ValueError('Invalid block size')
        n=round(self.duration*self.rate);flux=np.zeros((n,6));traces=[];nv=self.n+self.na;peakforce=np.zeros(self.na);balance=0.;minj=2.;maxj=0.;peakpen=0.;start=time.monotonic();stride=self.rate//120
        initial_volume=np.prod(self.scene['solid']['geometry']['size_m'])
        for at in range(0,n,block_frames):
            b=self.process(min(block_frames,n-at));p=b[:,:3*nv].reshape(-1,nv,3);v=b[:,3*nv:6*nv].reshape(-1,nv,3)
            fp=p[:,self.faces];av=.5*np.cross(fp[:,:,1]-fp[:,:,0],fp[:,:,2]-fp[:,:,0]);fv=v[:,self.faces].mean(axis=2)
            q=np.einsum('bfi,bfi->bf',av,fv)
            for g in range(6):flux[at:at+len(b),g]=q[:,self.groups==g].sum(axis=1)
            pick=(np.arange(at,at+len(b))%stride)==0
            traces.append(np.column_stack([((np.arange(at,at+len(b))[pick]+1)/self.rate),b[pick]]))
            peakforce=np.maximum(peakforce,b[:,6*nv:6*nv+self.na].max(axis=0));balance=max(balance,float(abs(b[:,-4]).max()));minj=min(minj,b[:,-3].min());maxj=max(maxj,b[:,-2].max());peakpen=max(peakpen,b[:,-1].max())
        energy,work,loss,_,_,_,_=b[-1,-7:]
        report={'schema':'coupled-solids-result/1','kernel_sha256':self.kernel_sha256,'engine':'SimulationEngine','backend':'tetrahedral finite-strain solid + translating compliant contact actors',
            'frames_internal':n,'internal_rate':self.rate,'vertices':self.n,'tetrahedra':len(self.tets),'surface_triangles':len(self.faces),'fingertips':self.na,'mass_kg':initial_volume*self.rho,'volume_formulation':self.scene['solid'].get('volume_formulation','element'),
            'peak_normal_forces_n':peakforce.tolist(),'max_contact_layer_compression_m':float(peakpen),'min_jacobian':float(minj),'max_jacobian':float(maxj),
            'energy_j':float(energy),'actuator_work_j':float(work),'dissipation_j':float(loss),'max_balance_error_j':balance,'balance_relative_to_net_work':balance/max(abs(work),1e-12),
            'render_seconds':time.monotonic()-start,'source_domain':'six surface-patch volume velocities m3/s','recording_input':False,'arbitrary_audio_excitation':False,'water_implemented':False,'human_listening_assessed':False,
            'scene_sha256':hashlib.sha256(json.dumps(self.scene,sort_keys=True).encode()).hexdigest()}
        trace=np.concatenate(traces)
        return {'flux':flux,'trace':trace,'report':report,'mesh':{'rest':self.rest,'faces':self.faces,'tets':self.tets,'groups':self.groups},'scene':self.scene}
    def render_binaural(self,*,gain=1.,block_frames=512):
        from .solid_sound import render_surface_sound
        result=self.render(block_frames=block_frames);audio,receiver=render_surface_sound(result,self.rate,gain)
        result['audio']=audio;result['report']['receiver']=receiver;return result
