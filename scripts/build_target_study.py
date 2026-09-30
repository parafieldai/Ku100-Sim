#!/usr/bin/env python3
"""Build a generated-audio-only target study. Supplied reference audio is NEVER published.

The two empirical models were fitted in the private research workspace. Building
this study uses only the pooled parameter files, not their source recordings.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ku100sim.audio import read_wav
from ku100sim.target_metrics import stats, compare_stats
from scripts.render_burst_source import render as render_burst
from scripts.render import render as render_native
ROOT = Path(__file__).resolve().parents[1]


def build(out: Path):
    if out.exists() or out.is_symlink():
        raise ValueError('Refusing to overwrite the generated target study; remove that known build output explicitly')
    if any(p.is_symlink() for p in out.absolute().parents):
        raise ValueError('Refusing linked build parents')
    refs = json.loads((ROOT/'validation/target/reference-targets.json').read_text())
    items = json.loads((ROOT/'research/target/triggers.json').read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.target-', dir=out.parent))
    try:
        entries=[]
        with tempfile.TemporaryDirectory(prefix='target-renders-') as folder:
            work=Path(folder)
            for slug, title, profile, seed, continuous in [
                ('burst-right-a','Empirical burst source / right A','right',90291,False),
                ('burst-right-b','Empirical burst source / right B','right',90292,False),
                ('burst-left-a','Empirical burst source / left','left',90291,False),
                ('continuous-right','Continuous-source negative control','right',90291,True)]:
                meta=render_burst(ROOT/f'models/burst-{profile}.json',work/slug,
                                  seconds=6., seed=seed, continuous_ablation=continuous)
                raw=(work/slug/'audio.wav').read_bytes(); (stage/(slug+'.wav')).write_bytes(raw)
                rate,x=read_wav(work/slug/'audio.wav')
                entries.append({'id':slug,'title':title,'kind':'ablation' if continuous else 'empirical',
                    'side':profile,'file':slug+'.wav','sha256':hashlib.sha256(raw).hexdigest(),
                    'metrics':stats(rate,x),'provenance':meta,
                    'claim':'Microphone-domain acoustic experiment; NOT simulated saliva, motion, force or a KU100 contact transfer.'})
            for side in ['right','left']:
                slug='fixture-'+side
                render_native(ROOT/f'scenes/target-baseline-{side}.json',work/slug)
                raw=(work/slug/'render.wav').read_bytes();(stage/(slug+'.wav')).write_bytes(raw)
                rate,x=read_wav(work/slug/'render.wav')
                meta=json.loads((work/slug/'native.json').read_text())
                entries.append({'id':slug,'title':'Previous generic fixture / '+side,'kind':'fixture',
                    'side':side,'file':slug+'.wav','sha256':hashlib.sha256(raw).hexdigest(),
                    'metrics':stats(rate,x),'provenance':{'native':meta,'scene_sha256':hashlib.sha256((ROOT/f'scenes/target-baseline-{side}.json').read_bytes()).hexdigest()},
                    'claim':'Existing plate/chamber/duct physics; REJECTED as a match to the requested target, not a tongue/ear model.'})
        comparisons=[]
        for ref in refs['references']:
            for entry in entries:
                if ref['side_label']==entry['side']:
                    comparisons.append({'reference':ref['id'],'candidate':entry['id'],
                                        **compare_stats(ref['metrics'],entry['metrics'])})
        study={'schema':'target-listening-study/1','target':'Close nonverbal wet mouth/artificial-ear sound',
               'status':'target_not_accepted','physical_target_implemented':False,
               'human_listening_performed':False,'reference_audio_public':False,
               'references':refs['references'],'candidates':entries,'comparisons':comparisons,
               'sources':items['sources'],'triggers':items['triggers'],
               'method':'Different fresh event sequences. Level-matched playback uses one scalar per stereo clip; it is not perceptual loudness matching. Original downloads are unchanged.',
               'limitations':['The reference action and microphone model are not physically verified.',
                   'Pooled event models do not reproduce the within-recording changes in spectrum or stereo balance.',
                   'Reference excerpts were excluded from these fits but previously inspected; this is not a blind held-out validation.',
                   'No arbitrary force, velocity, wetness or bubble identity is assigned to empirical controls.',
                   'No full-band, physical or perceptual acceptance claim is made.'],
               'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in [
                   'ku100sim/burst_source.py','ku100sim/target_metrics.py','scripts/fit_burst_source.py',
                   'scripts/build_target_study.py','models/burst-right.json','models/burst-left.json',
                   'validation/target/reference-targets.json','research/target/triggers.json']}}
        (stage/'study.json').write_text(json.dumps(study,indent=2,allow_nan=False)+'\n')
        stage.rename(out)
        return study
    finally:
        if stage.exists():shutil.rmtree(stage)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'web/target/generated');a=ap.parse_args()
    try:
        result=build(a.out)
        print(json.dumps({'out':str(a.out),'candidates':len(result['candidates']),'references_public':False,'target_accepted':False}))
    except (ValueError,OSError,RuntimeError) as exc:ap.exit(1,str(exc)+'\n')
