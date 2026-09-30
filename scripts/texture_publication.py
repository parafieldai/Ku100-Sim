"""Explicit publication boundary for generated source-iteration assets."""
from pathlib import Path
import base64

IDS=('revised-right-1','revised-right-2','revised-left-1','previous-right','previous-left','phase-control-right','phase-control-left')
APP=('source/index.html','source/app.js','source/style.css')
FILES=(*APP,'source/generated/iteration.json',*('source/generated/'+x+'.wav' for x in IDS))


def collect(source,read_file,decode_json,validate_audio):
    folder=source/'source'
    if not folder.exists():return {}
    if folder.is_symlink() or not folder.is_dir():raise ValueError('Invalid source iteration directory')
    generated=folder/'generated'
    if generated.is_symlink() or not generated.is_dir():raise ValueError('Invalid generated source directory')
    files={p:read_file(source/p,2*1024*1024) for p in APP}
    data=read_file(folder/'generated/iteration.json',512*1024)
    m=decode_json(data,'source iteration')
    if (m.get('schema')!='source-iteration/1' or m.get('reference_audio_public') is not False
            or m.get('physical_model') is not False or m.get('target_accepted') is not False):
        raise ValueError('Invalid source experiment status or privacy boundary')
    rows=m.get('samples',[])
    if not isinstance(rows,list) or len(rows)!=len(IDS) or {x.get('id') for x in rows}!=set(IDS):
        raise ValueError('Unexpected source iteration population')
    def no_raw(x,reference=False):
        if isinstance(x,dict):
            banned={'base64','raw_audio','reference_waveform','waveform_samples'}
            if reference:banned|={'audio','samples','waveform'}
            if banned&x.keys():raise ValueError('Raw reference payload prohibited')
            for v in x.values():no_raw(v,reference)
        elif isinstance(x,list):
            for v in x:no_raw(v,reference)
    no_raw(m)
    refs=m.get('reference_descriptors')
    if not isinstance(refs,list) or len(refs)!=4:raise ValueError('Reference descriptors missing')
    no_raw(refs,True)
    names={'iteration.json'}
    for row in rows:
        name=row.get('file')
        if name!=row['id']+'.wav' or row.get('kind') not in ('revision','previous','control'):
            raise ValueError('Invalid source filename or method')
        raw=read_file(folder/'generated'/name,3*1024*1024)
        if row.get('sample_rate')!=48000 or type(row.get('frames')) is not int or not 48000<=row['frames']<=12*48000+1023:
            raise ValueError('Invalid source audio shape')
        validate_audio({'mime':'audio/wav','channels':2,'base64':base64.b64encode(raw).decode(),'sha256':row['sha256']},48000,row['frames']/48000,name)
        files['source/generated/'+name]=raw;names.add(name)
    if {p.name for p in (folder/'generated').iterdir()}!=names:
        raise ValueError('Unlisted source iteration file')
    files['source/generated/iteration.json']=data
    return files
