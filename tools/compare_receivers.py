"""Measured-response and ideal-sphere comparison; never a wet-contact realism score."""
import hashlib,json,pathlib,subprocess,tempfile
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from sphere import transfer
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    measured=[];tests=[]
    frequencies=np.geomspace(200,8000,120);n=np.arange(128)
    for file in sorted((ROOT/'assets').glob('ku100_*.txt')):
        m=json.loads(file.with_suffix('.json').read_text());h=np.loadtxt(file)
        assert hashlib.sha256(file.read_bytes()).hexdigest()==m['fir_sha256']
        H=np.exp(-2j*np.pi*frequencies[:,None]*n/48000)@h
        az=m['azimuth_deg'];theta=np.cos(np.deg2rad([az-90,az+90]))
        S=transfer(frequencies,theta,distance=m['distance_m'])
        ild=20*np.log10(np.maximum(abs(H[:,0]),1e-15)/np.maximum(abs(H[:,1]),1e-15))
        sph=20*np.log10(abs(S[:,0])/abs(S[:,1]));bands={}
        for name,lo,hi in [('200_1000',200,1000),('1000_4000',1000,4000),('4000_8000',4000,8001)]:
            mask=(frequencies>=lo)&(frequencies<hi);bands[name]=float(np.mean(abs(ild[mask]-sph[mask])))
        measured.append({'file':file.name,'source_sha256':m['sofa_sha256'],'gain':m['distance_gain_applied'],'azimuth_deg':az,'distance_m':m['distance_m'],'broadband_ild_db':float(20*np.log10(np.linalg.norm(h[:,0])/np.linalg.norm(h[:,1]))),'peak_sample_indices':np.argmax(abs(h),axis=0).tolist(),'sphere_ild_mean_absolute_error_db':bands})
    # Native FIR path compared with a different convolution implementation.
    with tempfile.TemporaryDirectory() as td:
        base=pathlib.Path(td);identity=base/'identity.txt';identity.write_text('1 1\n')
        def run(name,filt):
            out=base/name;subprocess.run([str(ROOT/'build/ku100_sim'),'--seconds','.06','--modes','2','--receiver','measured','--filter',str(filt),'--out',str(out)],capture_output=True,check=True,timeout=120)
            return sf.read(out/'audio.wav',always_2d=True)[0]
        mono=run('identity',identity)[:,0]
        target=ROOT/'assets/ku100_0.25_90.txt';got=run('measured',target);h=np.loadtxt(target)
        expected=np.column_stack([fftconvolve(mono,h[:,e]) for e in [0,1]])
        for e in [0,1]:
            snr=float(20*np.log10(np.linalg.norm(expected[:,e])/np.linalg.norm(expected[:,e]-got[:,e])))
            tests.append({'check':f'native measured convolution channel {e}','snr_db':snr,'passed':snr>120})
    result={'checks':tests,'passed':all(x['passed'] for x in tests),'measurements':measured,'scope':'Receiver implementation accuracy and unfitted sphere discrepancy; no claim that ideal sphere or contact model matches KU100 wet-ear audio.'}
    (ROOT/'research/receivers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
