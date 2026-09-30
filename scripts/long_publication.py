"""Allowlist for the longer generated-only comparison; no imported references."""
from pathlib import Path
import base64
IDS=('fresh-right-a','fresh-right-b','fresh-left-a','long-right')
APP=('long/index.html','long/app.js')
FILES=(*APP,'long/generated/manifest.json',*('long/generated/'+x+'.wav' for x in IDS))

def collect(source,read_file,decode_json,validate_audio):
    folder=source/'long'
    if not folder.exists():return {}
    if folder.is_symlink() or not folder.is_dir():raise ValueError('Invalid long comparison folder')
    generated=folder/'generated'
    if generated.is_symlink() or not generated.is_dir():raise ValueError('Long examples must be generated before publishing')
    for p in folder.rglob('*'):
        if p.is_symlink():raise ValueError('Linked long comparison asset')
        if p.is_dir() and p==generated:continue
        if not p.is_file() or p.relative_to(source).as_posix() not in FILES:raise ValueError('Unlisted long comparison asset')
    files={p:read_file(source/p,2*1024*1024) for p in APP}
    raw=read_file(generated/'manifest.json',512*1024);m=decode_json(raw,'long examples')
    if m.get('schema')!='long-texture-examples/1' or m.get('physical_model') is not False or m.get('reference_audio_public') is not False or m.get('pressure_control_implemented') is not False:
        raise ValueError('Invalid long experiment scope')
    if m.get('source_recording_reads')!=0 or m.get('source_recording_read_attempts')!=0:
        raise ValueError('Unexpected audio input during generation')
    def no_raw(value):
        if isinstance(value,dict):
            if {'base64','reference_waveform','raw_audio','waveform_samples'}&value.keys():raise ValueError('Embedded raw audio forbidden')
            for v in value.values():no_raw(v)
        elif isinstance(value,list):
            for v in value:no_raw(v)
    no_raw(m)
    rows=m.get('samples',[])
    if len(rows)!=len(IDS) or {r.get('id') for r in rows}!=set(IDS):raise ValueError('Unexpected long example population')
    for row in rows:
        name=row.get('file');frames=row.get('frames')
        expected=(30 if row['id']=='long-right' else 12)*48000+1023
        if name!=row['id']+'.wav' or type(frames) is not int or frames!=expected or row.get('sample_rate')!=48000:raise ValueError('Invalid long example shape')
        b=read_file(generated/name,12*1024*1024)
        validate_audio({'mime':'audio/wav','channels':2,'base64':base64.b64encode(b).decode(),'sha256':row['sha256']},48000,frames/48000,name)
        files['long/generated/'+name]=b
    files['long/generated/manifest.json']=raw
    if {p.relative_to(source).as_posix() for p in folder.rglob('*') if p.is_file()}!=set(FILES):raise ValueError('Incomplete long comparison')
    return files
