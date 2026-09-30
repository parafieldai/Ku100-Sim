"""Strict generated-only PCM16 object-audition publication boundary.

Separate from the native Float32 bundle contract; no relaxation of that contract.
"""
from pathlib import Path
import hashlib
import struct
import numpy as np
from scripts.build_object_examples import IDS

APP=('objects/index.html','objects/app.js','objects/style.css')
FILES=(*APP,'objects/generated/manifest.json',*('objects/generated/'+x+'.wav' for x in IDS))


def validate_wav(raw, row):
    frames=row.get('frames')
    expected=48000 if row.get('kind')=='prior' else 4*48000
    if type(frames) is not int or frames!=expected or row.get('rate')!=48000 or row.get('channels')!=2 or row.get('pcm_bits')!=16:
        raise ValueError('Wrong object-audio metadata')
    if not isinstance(raw,bytes) or len(raw)!=44+4*frames or raw[:4]!=b'RIFF' or raw[8:16]!=b'WAVEfmt ' or raw[36:40]!=b'data':
        raise ValueError('Expected canonical PCM16 RIFF')
    if struct.unpack('<I',raw[4:8])[0]!=len(raw)-8 or struct.unpack('<IHHIIHH',raw[16:36])!=(16,1,2,48000,192000,4,16) or struct.unpack('<I',raw[40:44])[0]!=frames*4:
        raise ValueError('Invalid PCM16 format/size')
    if hashlib.sha256(raw).hexdigest()!=row.get('sha256'):
        raise ValueError('Audio identity mismatch')
    x=np.frombuffer(raw,dtype='<i2',offset=44).reshape(-1,2).astype(np.int32)
    if not np.array_equal(x[:,0],x[:,1]) or np.max(abs(x))>16385 or not np.any(x):
        raise ValueError('Expected bounded nonzero dual-mono object audition')


def collect(source, read_file, decode_json):
    source=Path(source);folder=source/'objects'
    if not folder.is_dir() or folder.is_symlink():raise ValueError('Missing object comparison')
    expected=set(FILES)
    for p in folder.rglob('*'):
        rel=p.relative_to(source).as_posix()
        if p.is_symlink() or not ((p.is_file() and rel in expected) or (p.is_dir() and rel=='objects/generated')):
            raise ValueError('Unlisted or linked object asset: '+rel)
    if {p.relative_to(source).as_posix() for p in folder.rglob('*') if p.is_file()}!=expected:
        raise ValueError('Incomplete object comparison')
    files={p:read_file(source/p,2*1024*1024) for p in APP}
    raw=read_file(folder/'generated/manifest.json',128*1024);m=decode_json(raw,'object preview')
    if m.get('schema')!='object-sfx-preview/1':raise ValueError('Invalid object schema')
    for flag in ('reference_audio_public','old_ear_recordings_used','render_from_recording','physical_calibration','pressure_control','raw_reference_audio_embedded'):
        if m.get(flag) is not False:raise ValueError('Invalid object scope: '+flag)
    if m.get('headphone_spatialization')!='dual mono, not KU100 transfer' or m.get('listener_judgment')!='not performed':
        raise ValueError('Unverified spatial/listening claim')
    def reject_raw(value):
        if isinstance(value,dict):
            if {'base64','waveform_samples','reference_waveform','raw_audio','residual_samples'} & value.keys():raise ValueError('Raw recording payload prohibited')
            for v in value.values():reject_raw(v)
        elif isinstance(value,list):
            for v in value:reject_raw(v)
    reject_raw(m)
    rows=m.get('samples')
    if not isinstance(rows,list) or len(rows)!=9 or any(not isinstance(r,dict) for r in rows) or {r.get('id') for r in rows}!=set(IDS):
        raise ValueError('Unexpected object sample population')
    for row in rows:
        name=row.get('file')
        if name!=row['id']+'.wav' or row.get('kind')!=row['id'].rsplit('-',1)[-1]:raise ValueError('Invalid object sample identity')
        data=read_file(folder/'generated'/name,1024*1024)
        validate_wav(data,row);files['objects/generated/'+name]=data
    files['objects/generated/manifest.json']=raw
    return files
