#!/usr/bin/env python3
"""Render the next source-only listening iteration from aggregate models.

No target waveform is opened by this script. Old/current/control sources share
a frozen inter-ear filter. The public build contains generated audio only.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,tempfile,time
import numpy as np
from scipy import signal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.texture_source import load,synthesize,frozen_stereo_transfer,RATE
from ku100sim.burst_source import load_model,synthesize as old_synth,wav_bytes
from ku100sim.target_metrics import stats

NAMES=('revised-right-1','revised-right-2','revised-left-1','previous-right','previous-left','phase-control-right','phase-control-left')

def phase_control(x,seed):
    """Change phases of GENERATED source only. Preserves pre-fade periodogram."""
    rng=np.random.default_rng(seed);z=np.fft.rfft(x);phi=rng.uniform(-np.pi,np.pi,len(z))
    new=abs(z)*np.exp(1j*phi);new[0]=z[0];
    if len(x)%2==0:new[-1]=z[-1]
    y=np.fft.irfft(new,n=len(x))
    error=float(np.linalg.norm(abs(np.fft.rfft(y))-abs(z))/max(np.linalg.norm(abs(z)),1e-12))
    if error>1e-10:raise ValueError('Phase-only control changed its spectrum')
    return y,error


def finish(source,old):
    x=np.array(source,dtype=float,copy=True)
    fade=480;w=.5-.5*np.cos(np.linspace(0,np.pi,fade));x[:fade]*=w;x[-fade:]*=w[::-1]
    y,route=frozen_stereo_transfer(old,x)
    near=old['near_channel']
    audible=signal.sosfilt(signal.butter(3,35,fs=RATE,btype='high',output='sos'),y[:,near])
    rms=np.sqrt(np.mean(audible**2));wanted=float(.04/max(rms,1e-12))
    gain=min(wanted,.6/max(float(abs(y).max()),1e-12));y*=gain
    if not np.isfinite(y).all() or abs(y).max()>.600001:raise ValueError('Invalid listening headroom')
    return y,route,{'method':'One scalar per stereo file; near-ear 35 Hz high-pass RMS measurement, target 0.04',
        'shared_gain':gain,'requested_gain':wanted,'static_peak_cap_active':bool(gain<wanted),
        'output_eq_applied':False,'boundary_fade_s':.01,'physical_loudness_calibrated':False}


def build(output,iterations=800):
    output=Path(output).absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('Use a new, non-symlink output directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.texture-',dir=output.parent))
    started=time.time();rows=[];cache={}
    try:
        old={side:load_model(ROOT/f'models/burst-{side}.json') for side in ['right','left']}
        def save(name,title,side,kind,x,info):
            audio,route,gain=finish(x,old[side]);raw=wav_bytes(audio)
            (stage/(name+'.wav')).write_bytes(raw)
            rows.append({'id':name,'title':title,'side':side,'near_channel':old[side]['near_channel'],
                'kind':kind,'file':name+'.wav','sha256':hashlib.sha256(raw).hexdigest(),
                'frames':len(audio),'sample_rate':RATE,'metrics':stats(RATE,audio),
                'fixed_route':route,'listening_level':gain,'generation':info})
            print('Rendered '+name,flush=True)
        for side,seed,label in [('right',307,'1'),('right',401,'2'),('left',307,'1')]:
            model_file=f'models/texture-{side}-reference.ctm.xz' if label=='1' else f'models/texture-{side}.ctm.xz'
            model=load(ROOT/model_file)
            x,info=synthesize(model,seed=seed,iterations=iterations,boundary_fade=False)
            if not info['best_objective'] < info['history'][0]['loss']*.5:
                raise ValueError('Texture optimization failed to improve its fitted objective')
            info['fitting_scope']=model['provenance'].get('fit_scope','disjoint_ranges')
            info['fitting_ranges_s']=model['provenance']['ranges_s']
            title=f'Revised source · {side}' if label=='1' else 'Range-fitted source · right'
            save(f'revised-{side}-{label}',title,side,'revision',x,info)
            if label=='1':cache[side]=x.copy()
        for side in ['right','left']:
            audio,info=old_synth(old[side],seconds=6,seed=90291)
            save('previous-'+side,'Previous burst source · '+side,side,'previous',audio[:,old[side]['near_channel']],info)
            x,err=phase_control(cache[side],197)
            save('phase-control-'+side,'Spectrum-matched control · '+side,side,'control',x,
                {'method':'Randomized phases of new generated source; not a new intended action',
                 'pre_fade_magnitude_relative_error':err,'seed':197,'runtime_reference_audio_reads':0,
                 'target_accepted':False})
        manifest={'schema':'source-iteration/1','reference_audio_public':False,
            'target_accepted':False,'physical_model':False,'human_listening_performed':False,
            'samples':rows,'elapsed_render_s':time.time()-started,
            'reference_descriptors':json.loads((ROOT/'validation/target/reference-targets.json').read_text())['references'],
            'controls':['Same fixed stereo filter within each side; no new spatial fitting.',
                        'All WAVs use a declared shared gain, not independently normalized ears.',
                        'Phase controls match their new source periodogram before the common boundary fade.',
                        'Listening remains necessary; these metrics are not an ASMR score.'],
            'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
                'ku100sim/texture_source.py','scripts/build_texture_iteration.py',
                'models/texture-left-reference.ctm.xz','models/texture-right-reference.ctm.xz','models/texture-right.ctm.xz',
                'models/burst-left.json','models/burst-right.json']}}
        (stage/'iteration.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
        stage.rename(output);return manifest
    finally:
        if stage.exists():shutil.rmtree(stage)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'web/source/generated');p.add_argument('--iterations',type=int,default=800);a=p.parse_args()
    m=build(a.out,a.iterations);print(json.dumps({'files':len(m['samples']),'seconds':m['elapsed_render_s'],'target_accepted':False}))
