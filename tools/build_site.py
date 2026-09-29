"""Run the real C++ engine, then package only explicitly allowed site files."""
from __future__ import annotations
import argparse,base64,hashlib,json,pathlib,shutil,subprocess,tempfile
import numpy as np
import soundfile as sf
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',default=str(ROOT/'build/ku100_sim'));p.add_argument('--out',type=pathlib.Path,default=ROOT/'_site');a=p.parse_args()
    if a.out.exists():raise FileExistsError('Site destination exists; choose a fresh directory')
    exe=str(pathlib.Path(a.exe).resolve());dest=a.out;dest.mkdir(parents=True)
    shutil.copyfile(ROOT/'web/index.html',dest/'index.html');(dest/'.nojekyll').touch(); demos=[]
    cases=[('stroke-left','Stroke / left contact',['--action','stroke']),('stroke-right','Stroke / right contact',['--action','stroke','--side','right']),('press-left','Press / left contact',['--action','press'])]
    measured=ROOT/'assets/ku100_0.25_90.txt'
    if measured.exists():cases.append(('ku100-air','KU100 25 cm / airborne only',['--action','stroke','--receiver','measured','--filter',str(measured)]))
    with tempfile.TemporaryDirectory(prefix='ku100-site-') as td:
        for name,title,settings in cases:
            out=pathlib.Path(td)/name
            args=[exe,'--seconds','1.2','--modes','6','--out',str(out),*settings]
            subprocess.run(args,check=True,capture_output=True,timeout=240)
            x,fs=sf.read(out/'audio.wav',always_2d=True);peak=float(abs(x).max());gain=.35/max(peak,1e-15)
            m=json.loads((out/'manifest.json').read_text());scene=dest/'demos'/name;scene.mkdir(parents=True)
            shutil.copyfile(out/'audio.wav',scene/'physical.wav')
            sf.write(scene/'preview.wav',x*gain,fs,subtype='PCM_16')
            trace=np.genfromtxt(out/'trace.csv',delimiter=',',names=True)
            # Reduced telemetry is strictly for visualization, not audio generation.
            fields=list(trace.dtype.names);telemetry=[{k:float(row[k]) for k in fields} for row in trace]
            m.update(preview_shared_gain=gain,physical_sha256=hashlib.sha256((out/'audio.wav').read_bytes()).hexdigest(),preview_sha256=hashlib.sha256((scene/'preview.wav').read_bytes()).hexdigest(),parameters={'seconds':1.2,'modes':6,'action':m['action'],'side':m['side'],'receiver':m['receiver']},contact_model_validated=False)
            (scene/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');(scene/'trace.json').write_text(json.dumps(telemetry,separators=(',',':'))+'\n')
            demos.append(dict(id=name,title=title,manifest=f'demos/{name}/manifest.json',trace=f'demos/{name}/trace.json',audio=f'demos/{name}/preview.wav',physical=f'demos/{name}/physical.wav'))
    (dest/'catalog.json').write_text(json.dumps({'version':1,'demos':demos,'render_source':'native C++','site_is_live_physics':False},indent=2)+'\n')
    docs=dest/'docs';docs.mkdir()
    for filename in ['PHYSICS.md','RESEARCH.md','VALIDATION.md']:
        src=ROOT/'docs'/filename
        if src.exists():shutil.copyfile(src,docs/filename)
    for filename in ['THIRD_PARTY_NOTICES.md','LICENSE']:
        src=ROOT/filename
        if src.exists():shutil.copyfile(src,dest/filename)
    # Fully offline companion; it embeds only this build's generated data, never user recordings.
    bundle={}
    for path in dest.rglob('*'):
        if path.suffix=='.json':bundle[str(path.relative_to(dest))]=json.loads(path.read_text())
        elif path.suffix=='.wav':bundle[str(path.relative_to(dest))]='data:audio/wav;base64,'+base64.b64encode(path.read_bytes()).decode()
    html=(dest/'index.html').read_text()
    embedded='<script>window.ku100Bundle='+json.dumps(bundle,separators=(',',':')).replace('</','<\\/')+';</script>'
    (dest/'offline.html').write_text(html.replace('<script>',embedded+'<script>',1))
    print(f'Built {len(demos)} native-rendered scenes: {dest}')
if __name__=='__main__':main()
