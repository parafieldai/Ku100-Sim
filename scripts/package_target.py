#!/usr/bin/env python3
"""Bundle the target listening comparison. References require an explicit local-only option.

Default CI/public package embeds generated audio only. --references produces a
private, user-owned review file and must never be copied into dist or committed.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.audio import read_wav
from scipy.io.wavfile import write as write_wav
import io

def module(text):return 'data:text/javascript;base64,'+base64.b64encode(text.encode()).decode()
def escape(value):return json.dumps(value,ensure_ascii=True).replace('<','\\u003c').replace('&','\\u0026')
def package(out:Path,references:Path|None=None):
    site=ROOT/'dist';resolved=out.resolve()
    if references and (resolved.is_relative_to(site.resolve()) or resolved.is_relative_to((ROOT/'web').resolve())):
        raise ValueError('Private reference comparison cannot be written into publication directories')
    if out.exists():raise ValueError('Refusing to overwrite a review file')
    names=['./target-study.json','./target-reference-summary.json','./triggers.json','./examples/wet-stroke-left.ku100.json']
    embedded={name:(site/name.removeprefix('./')).read_text() for name in names}
    study=json.loads(embedded['./target-study.json'])
    if study['reference_audio_included'] is not False or study['physical_target_accepted'] is not False:raise ValueError('Invalid source labels')
    refs=[]
    if references:
        summary=json.loads(embedded['./target-reference-summary.json'])
        for row in summary['references']:
            source=references/Path(row['filename']).name
            raw=source.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise ValueError('Reference identity changed: '+source.name)
            rate,x=read_wav(source);x=x[row['start_frame']:row['end_frame']]
            buffer=io.BytesIO();write_wav(buffer,rate,x.astype('<f4'));clip=buffer.getvalue()
            refs.append({'id':row['id'],'name':row['filename'],'start_s':row['start_s'],
                'source_sha256':row['source_sha256'],'sha256':hashlib.sha256(clip).hexdigest(),'base64':base64.b64encode(clip).decode()})
    core=module((site/'core.js').read_text())
    app=(site/'target.js').read_text().replace("'./core.js'",repr(core))
    loader="""const localFiles=JSON.parse(document.getElementById('embedded-target-files').textContent);
const nativeFetch=globalThis.fetch.bind(globalThis);
globalThis.fetch=(url,options)=>typeof url==='string'&&Object.hasOwn(localFiles,url)?Promise.resolve(new Response(localFiles[url],{headers:{'Content-Type':'application/json'}})):nativeFetch(url,options);
"""
    html=(site/'target.html').read_text().replace('<link rel="stylesheet" href="./target.css">','<style>'+(site/'target.css').read_text()+'</style>')
    data='<script id="embedded-target-files" type="application/json">'+escape(embedded)+'</script>'
    if refs:data+='<script id="private-reference-excerpts" type="application/json">'+escape(refs)+'</script>'
    html=html.replace('<script type="module" src="./target.js"></script>',data+'<script type="module" src="'+module(loader+app)+'"></script>')
    html=html.replace('href="./#engineering"','href="https://parafieldai.github.io/Ku100-Sim/#engineering"').replace('href="./"','href="https://parafieldai.github.io/Ku100-Sim/"')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(html)
    return {'file':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'reference_excerpts':len(refs),'private_reference_content':bool(refs),'generated_cases':len(study['cases'])}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--references',type=Path);a=ap.parse_args();print(json.dumps(package(a.out,a.references)))
