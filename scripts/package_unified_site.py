#!/usr/bin/env python3
"""Publish explicitly allowed shared-engine assets; no source recording inputs."""
import argparse,hashlib,json,shutil,tempfile,sys
from pathlib import Path
from scipy.io import wavfile
import io,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# Legacy packagers use script-relative imports; retain that unchanged contract.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scripts.build_site import ROOT,_read_file,_json,MAX_SITE_BYTES
from scripts.package_object_site import package as previous_package
from scripts.build_unified_examples import EXAMPLES
from ku100sim.unified import validate_scene
from ku100sim.binaural import require_binaural,BANK_SHA256,validate_microphone
APP=('unified/index.html','unified/app.js','unified/style.css')

def collect(source):
    folder=source/'unified';gen=folder/'generated'
    expected=set(APP)|{'unified/generated/manifest.json'}
    for slug,_ in EXAMPLES:expected.update('unified/generated/'+slug+ext for ext in ('.wav','.json','-trace.json'))
    if folder.is_symlink() or not folder.is_dir():raise ValueError('Invalid shared-engine folder')
    if any(p.is_symlink() for p in folder.rglob('*')):raise ValueError('Linked publication asset')
    actual={p.relative_to(source).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Missing or unexpected shared-engine asset')
    files={name:_read_file(source/name,4*1024*1024) for name in expected}
    m=_json(files['unified/generated/manifest.json'],'unified manifest')
    if m.get('schema')!='shared-mechanics-examples/1' or m.get('single_engine')!='SimulationEngine' or m.get('source_recordings_included') is not False or m.get('material_calibrated') is not False:raise ValueError('Invalid provenance')
    if len(m.get('samples',[]))!=len(EXAMPLES) or {x['id'] for x in m['samples']}!={x[0] for x in EXAMPLES}:raise ValueError('Invalid population')
    kernel=None
    for row in m['samples']:
        slug=row['id'];paths={'audio':slug+'.wav','scene':slug+'.json','trace':slug+'-trace.json'}
        for field,name in paths.items():
            if row[field]!=name or hashlib.sha256(files['unified/generated/'+name]).hexdigest()!=row['files_sha256'][name]:raise ValueError('Wrong asset identity')
        s=_json(files['unified/generated/'+row['scene']],'scene');duration,internal,p,*_=validate_scene(s)
        fs,a=wavfile.read(io.BytesIO(files['unified/generated/'+row['audio']]))
        if fs!=48000 or a.dtype!=np.float32 or a.shape!=(round(row['seconds']*fs),2) or not np.isfinite(a).all() or abs(a).max()>.80001:raise ValueError('Invalid generated listening WAV')
        require_binaural(a)
        r=row['report'];receiver=r.get('receiver',{})
        config=s.get('microphone');radius,_=validate_microphone(config,duration)
        expected=round(duration*fs)+int(radius/343*fs)+62+127
        if (receiver.get('bank_sha256')!=BANK_SHA256 or receiver.get('device')!='Neumann KU100'
            or receiver.get('configuration')!=config or receiver.get('output_frames')!=len(a)
            or len(a)!=expected or receiver.get('source_domain')!='weighted_surface_velocity_proxy'
            or m.get('head_or_microphone_simulated') is not True):raise ValueError('Missing or inconsistent measured binaural receiver')
        kh=r['kernel_sha256'];kernel=kernel or kh
        if kh!=kernel or r['recording_input'] is not False or r['calibrated_microphone'] is not False or r['relative_balance_error']>1e-6:raise ValueError('Inconsistent kernel/physical report')
        if r['scene_sha256']!=hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':')).encode()).hexdigest():raise ValueError('Scene/report mismatch')
        trace=_json(files['unified/generated/'+row['trace']],'trace')
        t=np.asarray(trace['time_s']);q=np.asarray(trace['coordinates_m'])
        if q.shape!=(len(t),len(p)) or not np.isfinite(q).all() or not np.all(np.diff(t)>0) or len(t)>8000:raise ValueError('Invalid coordinate trace')
    return files

def package(output):
    output=Path(output).absolute();source=ROOT/'web'
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Linked output')
    output=output.resolve()
    if output==source or source in output.parents or output in source.parents:raise ValueError('Output overlaps input')
    added=collect(source);output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.unified-site-',dir=output.parent))
    try:
        base=previous_package(stage);total=base['bytes']+sum(map(len,added.values()))
        if sum(map(len,added.values()))>24*1024*1024 or total>MAX_SITE_BYTES+24*1024*1024:
            raise ValueError('Bounded extension exceeds 24 MiB (previous site retains its 80 MiB limit)')
        for name,data in added.items():p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        names=set(base['files'])|set(added);dirs={p.as_posix() for name in names for p in Path(name).parents if p.as_posix()!='.'}
        if output.exists():
            if not output.is_dir():raise ValueError('Invalid output')
            for p in output.rglob('*'):
                rel=p.relative_to(output).as_posix()
                if p.is_symlink() or not ((p.is_file() and rel in names) or (p.is_dir() and rel in dirs)):raise ValueError('Unexpected old output')
            shutil.rmtree(output)
        stage.replace(output);return {'output':str(output),'files':sorted(names),'bytes':total}
    finally:
        if stage.exists():shutil.rmtree(stage)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'dist');a=p.parse_args();print(json.dumps(package(a.out),indent=2))
