#!/usr/bin/env python3
"""Create a private comparison HTML with the user's exact reference crops.

Never part of CI or public site generation. User recordings must not be committed
or deployed merely because the page supports local reference comparison.
"""
from pathlib import Path
import argparse,base64,hashlib,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ku100sim.audio import read_wav
from ku100sim.burst_source import wav_bytes
ROOT=Path(__file__).resolve().parents[1]

def package(input_root,output):
    if output.exists():raise ValueError('Refusing to overwrite private comparison')
    study=json.loads((ROOT/'web/target/generated/study.json').read_text())
    assets={}
    for row in study['candidates']:
        raw=(ROOT/'web/target/generated'/row['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Stale generated study')
        assets[row['file']]=base64.b64encode(raw).decode()
    references={}
    for row in study['references']:
        paths=list(input_root.glob(f"live_stream_019_chapter_{row['chapter']:02}_*.wav"))
        if len(paths)!=1:raise ValueError('Exactly one matching chapter source is required')
        if hashlib.sha256(paths[0].read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Source reference differs from the frozen file')
        rate,x=read_wav(paths[0]);a,b=row['crop_frames'];crop=x[a:b]
        if hashlib.sha256(crop.astype('<f4').tobytes()).hexdigest()!=row['crop_pcm_f32_sha256']:raise ValueError('Reference crop samples changed')
        raw=wav_bytes(crop,rate);references[row['id']]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
    payload=json.dumps({'study':study,'assets':assets,'references':references},ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    html=(ROOT/'web/target/index.html').read_text();css=(ROOT/'web/target/style.css').read_text()
    sources=[(ROOT/'web/core.js').read_text(),(ROOT/'web/target/core.js').read_text(),(ROOT/'web/target/app.js').read_text()]
    code='\n'.join(re.sub(r'^import .*?;\n','',s,flags=re.M) for s in sources)
    code=re.sub(r'export\s+\{[^}]*\};','',code)
    code=re.sub(r'\bexport\s+(?=(?:async\s+)?(?:function|const|class|let)\b)','',code)
    html=html.replace('<link rel="stylesheet" href="./style.css">','<style>'+css+'</style>')
    html=html.replace('href="../"','href="https://parafieldai.github.io/Ku100-Sim/"')
    html=html.replace('<script type="module" src="./app.js"></script>',
        '<script>window.__TARGET_INLINE__='+payload+';</script><script type="module">'+code.replace('</script','<\\/script')+'</script>')
    html=html.replace('<title>Target listening · Parafield</title>','<title>Private reference comparison · Parafield</title>')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(html)
    return {'file':output.name,'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'private_reference_crops_included':True,'public_deployment_permitted':False,'references':len(references),'generated_examples':len(assets)}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    try:print(json.dumps(package(a.input_root,a.out)))
    except (ValueError,OSError) as exc:ap.exit(1,str(exc)+'\n')
