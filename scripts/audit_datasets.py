#!/usr/bin/env python3
"""Read-only, size-bounded public dataset inspection. Never executes dataset code.

Dataset files remain private research artifacts, never site assets. A public
metadata license is recorded, not assumed to clear every linked performance.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
import zipfile

LIMIT = 64 * 1024 * 1024
class Fetch:
    def __init__(self): self.used=0; self.receipts=[]
    def get(self,url,limit=2*1024*1024,headers=None):
        request=urllib.request.Request(url,headers={'User-Agent':'Ku100-Sim research audit/1.0',**(headers or {})})
        with urllib.request.urlopen(request,timeout=50) as r:
            data=r.read(min(limit,LIMIT-self.used)+1)
            if len(data)>limit or self.used+len(data)>LIMIT: raise ValueError('Audit download budget exceeded')
            self.used+=len(data)
            receipt={'url':url,'final_url':r.url,'status':r.status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'content_type':r.headers.get('Content-Type'),'content_range':r.headers.get('Content-Range')}
        self.receipts.append(receipt);return data,receipt
    def json(self,url):return json.loads(self.get(url)[0])

class RemoteFile(io.RawIOBase):
    def __init__(self,url,size,fetch): self.url=url;self.size=size;self.fetch=fetch;self.pos=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=(0 if whence==0 else self.pos if whence==1 else self.size)+offset
        if self.pos<0:raise ValueError('Negative remote offset')
        return self.pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        if n<=0:return b''
        if n>24*1024*1024:raise ValueError('Single remote range exceeds 24 MiB')
        start=self.pos;data,receipt=self.fetch.get(self.url,limit=n,headers={'Range':f'bytes={start}-{start+n-1}'})
        if receipt['status']!=206 or not (receipt['content_range'] or '').startswith(f'bytes {start}-') or len(data)!=n:
            raise ValueError('Server did not honor the requested byte range')
        self.pos+=n;return data

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('validation/local/dataset-audit'));args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    f=Fetch();report={'checked_utc':datetime.now(timezone.utc).isoformat(),'datasets':[],'not_calibrated_ku100_data':True}
    def attempt(name,fn):
        row={'name':name}
        try:row.update(fn())
        except Exception as e:row.update({'status':'unavailable_or_incomplete','error':str(e)[:500]})
        report['datasets'].append(row)
    def hf(repo):
        j=f.json('https://huggingface.co/api/datasets/'+repo)
        card,rec=f.get('https://huggingface.co/datasets/'+repo+'/resolve/'+j['sha']+'/README.md')
        text=card.decode('utf-8');(args.out/(repo.replace('/','__')+'.md')).write_text(text)
        return {'status':'metadata_and_card_inspected','revision':j['sha'],'license':j.get('cardData',{}).get('license'),'fields':j.get('cardData',{}).get('dataset_info',{}),'files':[x['rfilename'] for x in j.get('siblings',[])][:40],'card_sha256':rec['sha256'],'audio_trials_inspected':0}
    for repo in ['OOPPEENN/ASMR_Dataset','nyuuzyou/asmr','Leying/DeepASMR-dataset','OmniAICreator/ASMR-Archive-Processed']:
        attempt(repo,lambda repo=repo:hf(repo))
    def kaggle():
        j=f.json('https://www.kaggle.com/api/v1/datasets/list?search=asmr&page=1&pageSize=10')
        (args.out/'kaggle-search.json').write_text(json.dumps(j,indent=2))
        return {'status':'public_metadata_inspected','results':j,'audio_trials_inspected':0}
    attempt('Kaggle ASMR search',kaggle)
    def cluster():
        j=f.json('https://api.figshare.com/v2/articles/29438288');(args.out/'cluster-metadata.json').write_text(json.dumps(j,indent=2))
        row={'status':'record_inspected','doi':j.get('doi'),'license':j.get('license'),'files':[{k:x.get(k) for k in ['name','id','size','computed_md5','download_url']} for x in j['files']], 'sample_trials':[]}
        files=[x for x in j['files'] if x['name'].lower().endswith('.zip')]
        if not files:return row
        selected=sorted(files,key=lambda x:(not ('texture' in x['name'].lower()),x['size']))[0]
        try:
            with zipfile.ZipFile(RemoteFile(selected['download_url'],selected['size'],f)) as z:
                entries=z.infolist();row['archive_entries']=len(entries)
                candidates=[i for i in entries if '/raw_audio/' in i.filename and i.filename.endswith('.wav')]
                if not candidates:row['archive_sample_paths']=[i.filename for i in entries[:30]];return row
                chosen=sorted(candidates,key=lambda i:i.filename)[0]; stem=Path(chosen.filename).stem
                paths=[chosen]+[i for i in entries if Path(i.filename).stem==stem and any('/'+k+'/' in i.filename for k in ['force','accel','position','audio'])]
                for info in paths:
                    if info.file_size>8*1024*1024:continue
                    raw=z.read(info);name=hashlib.sha256(info.filename.encode('utf-8')).hexdigest()[:16]+'-'+Path(info.filename).name;loc=args.out/'cluster-sample'/name;loc.parent.mkdir(parents=True,exist_ok=True);loc.write_bytes(raw)
                    item={'path':info.filename,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                    if info.filename.endswith('.wav'):
                        import soundfile as sf
                        with sf.SoundFile(io.BytesIO(raw)) as audio:item.update({'rate':audio.samplerate,'channels':audio.channels,'frames':audio.frames,'seconds':len(audio)/audio.samplerate,'subtype':audio.subtype})
                    else:
                        lines=raw.decode('utf-8-sig').splitlines();item.update({'line_count':len(lines),'first_lines':lines[:4]})
                    row['sample_trials'].append(item)
                row['status']='representative_paired_trial_inspected' if len(row['sample_trials'])>=4 else 'partial_trial_inspected'
        except Exception as e:row['sample_access_error']=str(e)[:500]
        return row
    attempt('Cluster Haptic Texture Dataset',cluster)
    report['receipts']=f.receipts;report['downloaded_bytes']=f.used
    (args.out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'report':str(args.out/'report.json'),'statuses':[(r['name'],r['status']) for r in report['datasets']]}))
if __name__=='__main__':main()
