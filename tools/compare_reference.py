"""Descriptive, unpaired reference diagnostics. Never an acoustic-fidelity score."""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import welch

def describe(path,center_seconds=None):
    with sf.SoundFile(path) as f:
        duration=f.frames/f.samplerate;start=max(0,(duration-(center_seconds or duration))/2)
        f.seek(round(start*f.samplerate));x=f.read(frames=round(center_seconds*f.samplerate) if center_seconds else -1,always_2d=True);fs=f.samplerate
    if x.shape[1]!=2:raise ValueError('Stereo input required')
    rms=np.sqrt(np.mean(x*x,axis=0));hz,p=welch(x,fs=fs,nperseg=min(4096,len(x)),axis=0);total=p[(hz>=20)&(hz<20000)].sum(axis=0)
    bands={f'{lo}_{hi}':(p[(hz>=lo)&(hz<hi)].sum(axis=0)/np.maximum(total,1e-30)).tolist() for lo,hi in [(20,250),(250,1000),(1000,4000),(4000,16000),(16000,20000)]}
    return {'name':path.name,'duration_s':duration,'crop_start_s':start,'crop_duration_s':len(x)/fs,'sample_rate':fs,'rms':rms.tolist(),'left_minus_right_rms_db':float(20*np.log10(max(rms[0],1e-15)/max(rms[1],1e-15))),'band_power_fraction_20_20k':bands,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--references',type=pathlib.Path,required=True);p.add_argument('--simulation',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('research/reference-comparison.json'));a=p.parse_args()
    refs=sorted(a.references.glob('live_stream_019_chapter_*.wav'))
    if not refs:raise FileNotFoundError('No named reference recordings found')
    result={'simulation':describe(a.simulation),'references':[describe(x,6) for x in refs],'matched_controlled_recordings':False,'interpretation':'Fixed center excerpts, not matched forces/actions or verified microphone provenance. Spectrum and channel balance are descriptive; do not interpret closeness as a fidelity or ASMR verdict.'};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
