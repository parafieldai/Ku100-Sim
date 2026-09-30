#!/usr/bin/env python3
"""Bounded RealImpact acquisition. Partial ZIP CRC is never claimed verified.
Recordings are research inputs only, never runtime or Pages sound assets.
"""
import io,json,hashlib,urllib.request,zipfile,argparse,time
from pathlib import Path
import numpy as np
OBJECTS=('27_WoodPlate','64_CeramicMug','94_GlassGoblet')
class Remote(io.RawIOBase):
 def __init__(self,url):
  self.url=url;self.pos=0;self.used=0;self.receipts=[];self.cache={}
  req=urllib.request.Request(url,headers={'Range':'bytes=0-0'})
  with urllib.request.urlopen(req,timeout=60) as r:
   if r.status!=206:raise ValueError('Range access required')
   self.size=int(r.headers['Content-Range'].split('/')[-1]);r.read(2)
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,n,whence=0):
  self.pos=n+(0 if whence==0 else self.pos if whence==1 else self.size)
  if self.pos<0:raise ValueError('Negative offset')
  return self.pos
 def read(self,n=-1):
  n=min(n if n>=0 else self.size-self.pos,self.size-self.pos)
  if n<=0:return b''
  if n>32*1024*1024:raise ValueError('Large single request')
  start=self.pos;end=start+n;parts=[];bs=4*1024*1024
  for index in range(start//bs,(end-1)//bs+1):
   if index not in self.cache:
    a=index*bs;b=min(a+bs,self.size)-1
    if self.used+b-a+1>256*1024*1024:raise ValueError('Object network budget exceeded')
    req=urllib.request.Request(self.url,headers={'Range':f'bytes={a}-{b}'})
    for attempt in range(3):
     try:
      with urllib.request.urlopen(req,timeout=60) as r:
       data=r.read(b-a+2)
       if r.status!=206 or len(data)!=b-a+1 or not r.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise ValueError('Incorrect range response')
      break
     except Exception:
      if attempt==2:raise
      time.sleep(2)
    self.used+=len(data);self.receipts.append({'range':[a,b],'sha256':hashlib.sha256(data).hexdigest()});self.cache[index]=data
    if len(self.cache)>8:self.cache.pop(next(iter(self.cache)))
   data=self.cache[index];a=index*bs;parts.append(data[max(0,start-a):min(bs,end-a)])
  self.pos=end;return b''.join(parts)

def prefix(z,info,indices):
 with z.open(info) as f:
  version=np.lib.format.read_magic(f)
  if version not in ((1,0),(2,0)):raise ValueError('Unsupported NPY version')
  shape,order,dtype=(np.lib.format.read_array_header_1_0(f) if version==(1,0) else np.lib.format.read_array_header_2_0(f))
  if order or dtype.hasobject or len(shape)<1 or max(indices)>=shape[0]:raise ValueError('Unsupported NPY layout')
  rowbytes=int(np.prod(shape[1:]))*dtype.itemsize
  if rowbytes*(max(indices)+1)>128*1024*1024:raise ValueError('Expanded prefix budget exceeded')
  selected=[]
  for i in range(max(indices)+1):
   raw=f.read(rowbytes)
   if len(raw)!=rowbytes:raise ValueError('Truncated row')
   if i in indices:selected.append(np.frombuffer(raw,dtype=dtype).reshape(shape[1:]).copy())
 return np.stack(selected),{'full_shape':list(shape),'dtype':str(dtype),'selected_indices':indices,'full_member_crc_checked':False,'member_crc_declared':info.CRC}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('validation/local/impact-data'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 report={'dataset':'RealImpact, Clarke et al., CVPR 2023','project':'https://samuelpclarke.com/realimpact/','sample_rate':48000,'sample_rate_basis':'Primary paper section 4.1','objects':[],'reference_waveforms_for_site':False}
 for name in OBJECTS:
  row={'object':name,'arrays':[]};report['objects'].append(row)
  try:
   remote=Remote('https://downloads.cs.stanford.edu/viscam/RealImpact/'+name+'.zip');folder=a.out/name;folder.mkdir()
   row.update({'url':remote.url,'archive_bytes':remote.size})
   with zipfile.ZipFile(remote) as z:
    entries=z.infolist();row['entries']=[{'name':i.filename,'bytes':i.file_size,'compressed':i.compress_size} for i in entries]
    for base,inds in [('deconvolved_0db.npy',[7,22,37,52]),('sounds.npy',[7,22,37,52]),('hammers.npy',[0,1,2,3]),('hammer_newtons.npy',[0,1,2,3]),('listenerXYZ.npy',[7,22,37,52]),('vertexID.npy',[7,22,37,52]),('vertexXYZ.npy',[7,22,37,52])]:
     matches=[i for i in entries if Path(i.filename).name==base]
     if not matches:row['arrays'].append({'name':base,'status':'not in archive'});continue
     data,meta=prefix(z,matches[0],inds);dest=folder/base;np.save(dest,data,allow_pickle=False)
     row['arrays'].append({'name':base,'status':'selected rows extracted','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),**meta})
   row.update({'status':('audio subset extracted' if any(x['name']=='deconvolved_0db.npy' and 'sha256' in x for x in row['arrays']) else 'metadata only'),'network_bytes':remote.used,'ranges':remote.receipts})
  except Exception as e:row.update({'status':'failed','error':str(e)})
  (a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(name,row['status'],row.get('error',''),flush=True)
 if any(r['status']!='audio subset extracted' for r in report['objects']):raise SystemExit('At least one requested audio subset was unavailable; see receipt.json')
if __name__=='__main__':main()
