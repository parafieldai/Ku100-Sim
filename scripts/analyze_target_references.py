#!/usr/bin/env python3
"""Inspect supplied WAV targets without publishing their audio or inventing action labels."""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.audio import read_wav
from ku100sim.target_metrics import stats

def inspect(root):
    rows=[]
    for ch,start,side in [(3,57.,'right'),(5,64.,'right'),(4,89.,'left'),(6,51.5,'left')]:
        paths=list(root.glob(f'live_stream_019_chapter_{ch:02d}_*.wav'))
        if len(paths)!=1:raise ValueError('Need exactly one source file for chapter '+str(ch))
        p=paths[0];rate,x=read_wav(p);end=start+6
        crop=x[round(start*rate):round(end*rate)]
        rows.append({'id':f'chapter-{ch:02d}','title':f'Chapter {ch:02d} / {side}-labelled reference',
                     'chapter':ch,'side_label':side,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'source_rate_hz':rate,'source_frames':len(x),'source_channels':x.shape[1],
                     'crop_s':[start,end],'crop_frames':[round(start*rate),round(end*rate)],
                     'crop_pcm_f32_sha256':hashlib.sha256(crop.astype('<f4').tobytes()).hexdigest(),
                     'status':'local-reference-required','physical_action':'unverified',
                     'device':'unverified','source_split':'excluded from current parameter fit; previously inspected, not a blind test',
                     'metrics':stats(rate,crop)})
    return {'schema':'target-reference-spec/1','target':'Nonverbal close wet mouth/artificial-ear interaction from the user-provided references',
            'reference_audio_public':False,'target_user_acceptance':'not_assessed',
            'calibrated_contact_data':False,'references':rows,
            'excluded':'Chapter 02 is labelled as mixed objects/mouth/reverb and is not an isolated primary target.',
            'required_behavior':['slide','rolling contact','peel','release','prior-contact dependence','synchronized genuine stereo'],
            'event_labels':'Acoustic peaks are detector proposals, NOT observed peel/bubble/suction events.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite frozen reference report')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(inspect(a.input_root),indent=2,allow_nan=False)+'\n')
