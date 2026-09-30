"""Shared measured KU100 receiver. Stereo is an export requirement, not a panner.

The compact source is an approximation, NOT an identified emitted field. The
measured bank describes airborne capture only: no ear contact, 3Dio calibration,
source-specific directivity or absolute Pa inference is asserted.
"""
from __future__ import annotations
import ctypes as ct
import hashlib
import json
import math
from pathlib import Path
import subprocess
import threading
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RATE=48000
BANK_SHA256='8b781cf38083c47ee4264ca9594289a35dda53b893bd794cba8803d471515712'
RADII=(.25,.5,.75,1.,1.5)
_LOCK=threading.Lock()
DOMAINS=('weighted_surface_velocity_proxy','effective_microphone_response','uncalibrated_modal_response','numerical_test')


def _number(x,lo,hi,name):
    try:ok=type(x) in (int,float) and math.isfinite(x) and lo<=x<=hi
    except OverflowError:ok=False
    if not ok:raise ValueError('Invalid '+name)
    return float(x)


def default_microphone(seconds):
    """A slow right-to-left arc; static side for short diagnostic sounds."""
    seconds=_number(seconds,.001,30,'duration')
    trajectory=([[0.,-75.],[seconds,-75.]] if seconds<3 else
                [[0.,-75.],[seconds*.1,-75.],[seconds*.9,75.],[seconds,75.]])
    return {'model':'KU100_NF','radius_m':.25,'azimuth_knots_deg':trajectory}


def validate_microphone(config,seconds):
    _number(seconds,.001,30,'duration')
    if not isinstance(config,dict) or set(config)!={'model','radius_m','azimuth_knots_deg'}:
        raise ValueError('Specify the measured microphone, radius and trajectory')
    if config['model']!='KU100_NF':
        raise ValueError('Only measured KU100_NF is available; 3Dio is not interchangeable')
    radius=_number(config['radius_m'],.25,1.5,'head-center radius')
    if radius not in RADII:
        raise ValueError('Use an actually measured radius; no distance interpolation/extrapolation here')
    try:k=np.asarray(config['azimuth_knots_deg'],dtype=float)
    except (ValueError,TypeError,OverflowError) as e:raise ValueError('Invalid trajectory') from e
    if (k.ndim!=2 or k.shape[1]!=2 or not 2<=len(k)<=128 or not np.isfinite(k).all()
        or k[0,0]!=0 or k[-1,0]!=seconds or np.any(np.diff(k[:,0])<=0) or np.max(abs(k[:,1]))>720):
        raise ValueError('Trajectory must cover the entire source duration')
    # Quintic easing has maximum derivative 1.875. Restrict the approximation to
    # slowly moving, fixed-radius sources; no unsupported radial Doppler model.
    angular=float(np.max(abs(np.diff(k[:,1])/np.diff(k[:,0])))*1.875)
    if angular>100 or radius*math.radians(angular)>.5:
        raise ValueError('Motion exceeds the declared quasi-static receiver range')
    return radius,k


def angles_at(knots,t):
    i=np.clip(np.searchsorted(knots[:,0],t,side='right')-1,0,len(knots)-2)
    z=np.clip((t-knots[i,0])/(knots[i+1,0]-knots[i,0]),0,1)
    z=z*z*z*(10+z*(-15+6*z))
    return np.ascontiguousarray(knots[i,1]+z*(knots[i+1,1]-knots[i,1]))


def _library():
    files=[ROOT/'native/binaural/renderer.cpp',ROOT/'native/receiver.cpp',ROOT/'native/receiver.hpp']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    dest=ROOT/'build'/('binaural-'+digest[:16]+'.so')
    with _LOCK:
        if not dest.exists():
            dest.parent.mkdir(exist_ok=True);tmp=dest.with_suffix('.partial.so')
            subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Wpedantic','-fPIC','-shared',
                            str(files[0]),str(files[1]),'-o',str(tmp)],check=True)
            tmp.replace(dest)
    lib=ct.CDLL(str(dest));D=ct.POINTER(ct.c_double)
    lib.binaural_create.argtypes=[ct.c_char_p,ct.c_double];lib.binaural_create.restype=ct.c_void_p
    lib.binaural_taps.argtypes=[ct.c_void_p];lib.binaural_taps.restype=ct.c_int
    lib.binaural_process.argtypes=[ct.c_void_p,ct.c_int,D,D,D];lib.binaural_process.restype=ct.c_int
    lib.binaural_destroy.argtypes=[ct.c_void_p];lib.binaural_destroy.restype=None
    lib.binaural_error.restype=ct.c_char_p
    return lib,hashes


def stereo_metrics(audio):
    a=np.asarray(audio,dtype=float)
    if a.ndim!=2 or a.shape[1]!=2 or not len(a) or not np.isfinite(a).all():raise ValueError('Finite stereo required')
    power=np.mean(a*a,axis=0);total=float(power.sum())
    difference=float(np.sum((a[:,0]-a[:,1])**2))
    correlation=float(np.dot(a[:,0],a[:,1])/math.sqrt(max(float(np.dot(a[:,0],a[:,0])*np.dot(a[:,1],a[:,1])),1e-300)))
    return {'identical_channels':bool(np.array_equal(a[:,0],a[:,1])),
            'difference_energy_fraction':difference/max(float(np.sum(a*a)),1e-300),
            'rms_left_right':np.sqrt(power).tolist(),'correlation':correlation,
            'ild_l_minus_r_db':float(10*np.log10(max(power[0],1e-300)/max(power[1],1e-300))) if total else None}


def require_binaural(audio):
    metrics=stereo_metrics(audio)
    if min(metrics['rms_left_right'])<1e-12 or metrics['identical_channels'] or metrics['difference_energy_fraction']<1e-6:
        raise ValueError('No silent, single-active-channel or duplicated-mono object preview is allowed')
    return metrics


class BinauralMicrophone:
    """A stateful receiver shared by every object; no per-object algorithm lookup.

    Native processing retains the full convolution history across blocks. The
    fixed-radius common propagation delay is restored once, with 31 samples of
    separately reported fractional-delay latency. Complete filter tails survive.
    """
    def __init__(self,config,seconds,*,source_domain,bank_path=None):
        self.handle=None;self.finished=False;self.frame=0
        self.radius,self.knots=validate_microphone(config,seconds)
        if source_domain not in DOMAINS:raise ValueError('Unknown source signal domain')
        self.config=json.loads(json.dumps(config,allow_nan=False));self.seconds=float(seconds)
        self.source_domain=source_domain;self.expected=round(seconds*RATE)
        path=Path(bank_path) if bank_path else ROOT/'data/ku100_bank.bin'
        if not path.is_file() or path.is_symlink() or path.stat().st_size!=1843264:
            raise ValueError('Verified KU100 bank required; prepare_ku100.py --download')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=BANK_SHA256:raise ValueError('KU100 bank hash mismatch')
        self.lib,self.source_hashes=_library()
        self.handle=self.lib.binaural_create(str(path).encode(),self.radius)
        if not self.handle:raise RuntimeError(self.lib.binaural_error().decode())
        self.taps=self.lib.binaural_taps(self.handle)
        self.latency_s=self.radius/343.+31/RATE
    def close(self):
        if getattr(self,'handle',None):self.lib.binaural_destroy(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def __del__(self):self.close()
    def _process(self,x):
        n=len(x);t=np.maximum(0,(self.frame+np.arange(n))/RATE-self.latency_s)
        angles=angles_at(self.knots,t);y=np.empty((n,2),dtype=np.float64)
        ptr=lambda v:v.ctypes.data_as(ct.POINTER(ct.c_double))
        if self.lib.binaural_process(self.handle,n,ptr(x),ptr(angles),ptr(y)):
            self.finished=True;raise RuntimeError(self.lib.binaural_error().decode())
        self.frame+=n;return y
    def process(self,source):
        x=np.ascontiguousarray(source,dtype=np.float64)
        if (self.finished or not self.handle or x.ndim!=1 or not 1<=len(x)<=65536
            or self.frame+len(x)>self.expected or not np.isfinite(x).all()):raise ValueError('Invalid receiver block/state')
        return self._process(x)
    def finish(self):
        if self.finished or not self.handle or self.frame!=self.expected:raise ValueError('Complete source before finishing')
        y=self._process(np.zeros(self.taps-1));self.finished=True;return y
    def render(self,source,block_frames=2048):
        x=np.asarray(source,dtype=float)
        if self.frame or x.shape!=(self.expected,) or type(block_frames) is not int or not 1<=block_frames<=65536:
            raise ValueError('Fresh receiver and exact source duration required')
        blocks=[self.process(x[i:i+block_frames]) for i in range(0,len(x),block_frames)]
        blocks.append(self.finish());y=np.concatenate(blocks)
        return y,self.report(y)
    def report(self,audio):
        points=np.arange(0,self.seconds+1e-9,1/30)
        return {'schema':'measured-binaural-render/1','device':'Neumann KU100','method':'audio-rate interpolated measured horizontal HRIR',
                'configuration':self.config,'source_domain':self.source_domain,'source_representation':'compact point-source approximation',
                'bank_sha256':BANK_SHA256,'code_sha256':self.source_hashes,'input_sample_rate':RATE,'output_sample_rate':RATE,
                'source_frames':self.expected,'output_frames':len(audio),'full_filter_tail_frames':self.taps-1,
                'propagation_delay_s':self.radius/343.,'fractional_delay_processing_latency_s':31/RATE,
                'path_time_s':points.tolist(),'path_azimuth_deg':angles_at(self.knots,points).tolist(),
                'stereo':stereo_metrics(audio),'source_recording_playback':False,'device_calibrated_absolute_pressure':False,
                'direct_contact_or_seal_simulated':False,'source_directivity_identified':False,
                'original_source_capture_coloration_retained':self.source_domain=='effective_microphone_response',
                'rendered_distance_reference':'dummy-head center, NOT distance from ear',
                'limits':['0.25–1.50 m measured rings, horizontal airborne capture only',
                          'Slow fixed-radius trajectory; quasi-static interpolation, not a moving-boundary wave solver',
                          '200 Hz low-frequency extension is analytic; not measured contact validation',
                          'Source radiation/material fidelity and a human ASMR listening response are not established'],
                'attribution':{'authors':'Arend, Neidhardt, Poerschmann','source':'https://zenodo.org/records/4297951',
                               'embedded_license':'CC-BY-SA-3.0','metadata_license':'CC-BY-4.0',
                               'notice':'Source-file attribution and share-alike notice retained; no relicensing of receiver data'}}
