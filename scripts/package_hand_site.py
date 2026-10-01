#!/usr/bin/env python3
"""Extend the original allowlisted Pages site with measured-data contact research."""
from pathlib import Path
import sys,io,json,hashlib,shutil,tempfile,argparse
import numpy as np
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from scripts.package_unified_site import package as previous_package
from scripts.build_hand_scene import IDS
from ku100sim.solid_scene import validate
from ku100sim.binaural import require_binaural
FORK_IDS=('approach-rotate-256','ring-only-512','rotate-anchor-512','rotate-near-512','rotate-near-256','rotate-near-128','rotate-near-left-256')
APP=('hand/index.html','hand/style.css','hand/app.js','fork-radiation/index.html','fork-radiation/app.js')
def expected():
 names=set(APP)|{'hand/generated/manifest.json','hand/generated/refinement.json','fork-radiation/generated/manifest.json'}
 for k in IDS:names.update('hand/generated/'+k+ext for ext in ('.wav','.scene.json','.trace.json','.report.json'))
 for k in FORK_IDS:names.update('fork-radiation/generated/'+k+ext for ext in ('.wav','.scene.json','.report.json'))
 return names

def collect(source):
 source=Path(source);names=expected();files={}
 for dirname in ('hand','fork-radiation'):
  folder=source/dirname
  if folder.is_symlink() or not folder.is_dir():raise ValueError('Invalid extension folder')
  for p in folder.rglob('*'):
   if p.is_symlink():raise ValueError('Linked asset')
   rel=p.relative_to(source).as_posix()
   if p.is_file() and rel not in names and rel!='fork-radiation/offline-template.html':raise ValueError('Unlisted extension asset')
 for name in names:
  p=source/name
  if not p.is_file() or p.stat().st_size>5*1024*1024:raise ValueError('Missing or oversized asset '+name)
  files[name]=p.read_bytes()
 if sum(map(len,files.values()))>56*1024*1024:raise ValueError('Extension over budget')
 m=json.loads(files['hand/generated/manifest.json']);f=json.loads(files['fork-radiation/generated/manifest.json'])
 if m.get('schema')!='hand-contact-auditions/1' or m.get('raw_recordings_included') is not False or m.get('source_recordings_used') is not False or m.get('source_timbre_accepted') is not False or m.get('binaural_required') is not True or m.get('water_implemented') is not False or m.get('human_listening_assessment') is not None:raise ValueError('Invalid contact scope')
 if len(m.get('samples',[]))!=len(IDS) or {r.get('id') for r in m['samples']}!=set(IDS):raise ValueError('Invalid contact samples')
 for r in m['samples']:
  k=r['id'];s=json.loads(files['hand/generated/'+k+'.scene.json']);validate(s)
  for suffix in ('.wav','.scene.json','.trace.json','.report.json'):
   name=k+suffix
   if r.get('sha256',{}).get(name)!=hashlib.sha256(files['hand/generated/'+name]).hexdigest():raise ValueError('Hand hash mismatch')
  fs,a=wavfile.read(io.BytesIO(files['hand/generated/'+k+'.wav']))
  if fs!=48000 or a.dtype!=np.float32 or not np.isfinite(a).all() or abs(a).max()>.8 or len(a)!=round(r['seconds']*fs):raise ValueError('Bad contact WAV')
  require_binaural(a)
  t=json.loads(files['hand/generated/'+k+'.trace.json']);p=np.asarray(t['positions_mm']);tt=np.asarray(t['time_s']);force=np.asarray(t['forces_n'])
  if p.shape!=(len(tt),t['solid_vertices']+2,3) or not np.isfinite(p).all() or force.shape!=(len(tt),2) or not np.isfinite(force).all() or np.any(np.diff(tt)<=0):raise ValueError('Invalid geometry trace')
  if len(tt)>1000 or abs(p).max()>200:raise ValueError('Out-of-range trace')
 refinement=json.loads(files['hand/generated/refinement.json'])
 if refinement.get('schema')!='hand-scene-refinement/1' or refinement.get('asmr_acceptance') is not None:raise ValueError('Invalid refinement record')
 if f.get('schema')!='fork-radiation-auditions/1' or f.get('source_recordings_used') is not False or f.get('mono_output_allowed') is not False or f.get('physical_pressure_calibrated') is not False or f.get('human_listening_pass') is not None:raise ValueError('Invalid fork scope')
 if len(f.get('samples',[]))!=len(FORK_IDS) or {r.get('id') for r in f['samples']}!=set(FORK_IDS):raise ValueError('Wrong fork population')
 for r in f['samples']:
  k=r['id'];name=k+'.wav'
  if r['file']!=name or hashlib.sha256(files['fork-radiation/generated/'+name]).hexdigest()!=r['sha256']:raise ValueError('Fork hash mismatch')
  fs,a=wavfile.read(io.BytesIO(files['fork-radiation/generated/'+name]))
  if fs!=48000 or a.dtype!=np.float32 or a.shape!=(480000,2) or not np.isfinite(a).all() or abs(a).max()>.36:raise ValueError('Invalid fork WAV')
  require_binaural(a)
 return files

def package(output):
 output=Path(output).absolute();source=ROOT/'web'
 if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Linked output')
 output=output.resolve()
 if output==source or source in output.parents or output in source.parents:raise ValueError('Output overlaps source')
 added=collect(source);output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.contact-site-',dir=output.parent))
 try:
  base=previous_package(stage);total=base['bytes']+sum(map(len,added.values()))
  if total>160*1024*1024:raise ValueError('Total site exceeds 160 MiB delivery budget')
  for name,b in added.items():p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  names=set(base['files'])|set(added);dirs={p.as_posix() for name in names for p in Path(name).parents if p.as_posix()!='.'}
  if output.exists():
   for p in output.rglob('*'):
    rel=p.relative_to(output).as_posix()
    if p.is_symlink() or not ((p.is_file() and rel in names) or (p.is_dir() and rel in dirs)):raise ValueError('Unexpected old output')
   shutil.rmtree(output)
  stage.replace(output);return {'output':str(output),'bytes':total,'files':sorted(names),'raw_recordings_published':False}
 finally:
  if stage.exists():shutil.rmtree(stage)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'dist');a=p.parse_args();print(json.dumps(package(a.out),indent=2))
