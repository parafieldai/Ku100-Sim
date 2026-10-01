#!/usr/bin/env python3
"""Generate contact-driven binaural sound and actual finite-element surface traces."""
from pathlib import Path
import argparse,hashlib,io,json,sys,time
import numpy as np
from scipy.io import wavfile
from scipy import signal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.unified import SimulationEngine
from ku100sim.solid_sound import render_surface_sound
from ku100sim.binaural import require_binaural
from scripts.make_hand_scenes import scene
IDS=('rub','light','rate-neutral','hold')
GAIN=600. # One fixed pairwise gain, not independent normalization or pressure units.

def spectral_summary(audio):
 near=audio[round(1.1*48000):round(3.25*48000),1];f,p=signal.welch(near,48000,nperseg=8192)
 mask=(f>=20)&(f<20000);total=p[mask].sum();peak=int(np.argmax(p*mask))
 return {'interval_s':[1.1,3.25],'near_channel':1,'peak_welch_bin_hz':float(f[peak]),'frequency_bin_hz':float(f[1]-f[0]),
         'band_power_fraction':{str(lo)+'-'+str(hi):float(p[(f>=lo)&(f<hi)].sum()/max(total,1e-30)) for lo,hi in [(20,100),(100,250),(250,500),(500,1000),(1000,4000),(4000,20000)]}}

def build(out,cache=None):
 out=Path(out)
 if out.exists() or out.is_symlink():raise ValueError('Use a fresh output path')
 out.mkdir(parents=True);rows=[]
 for kind in IDS:
  s=scene(kind)
  if cache:
   data=np.load(Path(cache)/(kind+'.npz'));old=json.loads((Path(cache)/(kind+'.json')).read_text())
   if old['scene']!=s:raise ValueError('Cached scene mismatch')
   r={'flux':data['flux'],'trace':data['trace'],'mesh':{k:data[k] for k in ('rest','faces','tets','groups')},'scene':s,'report':old['report']}
  else:
   with SimulationEngine(s) as engine:r=engine.render(block_frames=512)
  audio,receiver=render_surface_sound(r,s['internal_rate'],GAIN);require_binaural(audio)
  report=r['report'];report['receiver']=receiver;report['audio_analysis']=spectral_summary(audio)
  # Derive strain checks from sampled actual geometry, not just the determinant.
  mesh=r['mesh'];nv=len(mesh['rest'])+len(s['fingertips']);trace=r['trace'];pos=trace[:,1:1+3*nv].reshape(-1,nv,3)
  dm=(mesh['rest'][mesh['tets'][:,1:]]-mesh['rest'][mesh['tets'][:,:1]]).transpose(0,2,1);inv=np.linalg.inv(dm)
  f=np.einsum('btij,tjk->btik',(pos[:,mesh['tets'][:,1:]]-pos[:,mesh['tets'][:,:1]]).transpose(0,1,3,2),inv)
  sv=np.linalg.svd(f,compute_uv=False);report['sampled_principal_stretch_min_max']=[float(sv.min()),float(sv.max())];report['principal_stretch_sample_hz']=120
  stored=trace[:,-7];report['balance_relative_to_peak_stored_energy']=report['max_balance_error_j']/max(float(abs(stored).max()),1e-12)
  report['max_contact_compression_over_assumed_skin_layer']=report['max_contact_layer_compression_m']/min(a['skin_layer_m'] for a in s['fingertips'])
  dec=slice(None,None,2);b=trace[dec];p=pos[dec]
  state={'schema':'hand-geometry-trace/1','positions_mm':np.round(p*1000,5).tolist(),'time_s':b[:,0].tolist(),'faces':mesh['faces'].tolist(),'solid_vertices':len(mesh['rest']),
    'fingertip_radii_mm':[a['radius_m']*1000 for a in s['fingertips']],'forces_n':b[:,1+6*nv:1+6*nv+2].tolist(),'slipping_area_mm2':(b[:,1+6*nv+2:1+6*nv+4]*1e6).tolist(),
    'energy_j':b[:,-7].tolist(),'min_jacobian':b[:,-3].tolist(),'max_jacobian':b[:,-2].tolist(),'scene':s,
    'display_limits':'60 Hz sampled mechanics; no invented water, joint motion or microphone pressure. Spheres are compliant-layer proxies, not a full anatomical hand.'}
  raw=io.BytesIO();wavfile.write(raw,48000,audio.astype('float32'))
  assets={kind+'.wav':raw.getvalue(),kind+'.scene.json':(json.dumps(s,indent=2)+'\n').encode(),kind+'.trace.json':(json.dumps(state,separators=(',',':'),allow_nan=False)+'\n').encode(),kind+'.report.json':(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()}
  for name,data in assets.items():(out/name).write_bytes(data)
  rows.append({'id':kind,'title':s['name'],'seconds':len(audio)/48000,'source_seconds':s['duration_s'],'audio':kind+'.wav','scene':kind+'.scene.json','trace':kind+'.trace.json','report':kind+'.report.json',
    'sha256':{name:hashlib.sha256(data).hexdigest() for name,data in assets.items()},'peak':float(abs(audio).max()),'rms':np.sqrt(np.mean(audio*audio,axis=0)).tolist(),'forces_n':report['peak_normal_forces_n'],'kernel_sha256':report['kernel_sha256'],'gain':GAIN})
  print(kind,json.dumps({'forces':report['peak_normal_forces_n'],'peak':rows[-1]['peak'],'peak_bin':report['audio_analysis']['peak_welch_bin_hz']}),flush=True)
 manifest={'schema':'hand-contact-auditions/1','samples':rows,'single_api':'SimulationEngine','binaural_required':True,'raw_recordings_included':False,'source_recordings_used':False,
    'material':'Ecoflex 00-30 effective compression approximation; skin contact and acoustic damping remain assumed','force_is_not_capsule_pressure':True,'source_timbre_accepted':False,
    'water_implemented':False,'self_contact_implemented':False,'anatomical_hand_implemented':False,'hand_proxy':'Two translating compliant spherical fingertips with actuator reaction',
    'audio_mesh_converged':False,'human_listening_assessment':None,'acoustic_backend':'6 surface flux derivative sources projected onto a measured 0.25 m KU100 ring',
    'listening_policy':'One gain of 600 for all scenes and both ears; no independent leveling, loops, added bass or source recording playback',
    'known_limits':['Smooth solid-pad compression can be quiet; no fabricated squish','Remaining friction/radiation tonal character is not an established skin/silicone sound','Numerical surface-source convergence must be read separately from force convergence','Two-way fingertip/pad forces are implemented; finger joints and anatomical skin are not']}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n');return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'web/hand/generated');p.add_argument('--cache',type=Path);a=p.parse_args();build(a.out,a.cache)
