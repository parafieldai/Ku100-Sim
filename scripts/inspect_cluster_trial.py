#!/usr/bin/env python3
"""Inspect a bounded paired sample, without downloading the entire archive."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import zipfile
from audit_datasets import Fetch, RemoteFile

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('validation/local/dataset-audit/paired-trial'));a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    f=Fetch();report={'checked_utc':datetime.now(timezone.utc).isoformat(),'status':'unavailable','samples':[]}
    try:
        meta=f.json('https://api.figshare.com/v2/articles/29438288')
        report.update({'doi':meta['doi'],'license':meta['license']})
        candidates=[x for x in meta['files'] if x['name'].endswith('.zip') and 'mini' not in x['name'].lower()]
        source=min(candidates,key=lambda x:x['size']);report['archive']=source
        with zipfile.ZipFile(RemoteFile(source['download_url'],source['size'],f)) as z:
            entries=z.infolist();report['archive_entries']=len(entries)
            waves=[i for i in entries if '/raw_audio/' in i.filename and i.filename.endswith('.wav')]
            if not waves:
                report['wav_sample_paths']=[i.filename for i in entries if i.filename.endswith('.wav')][:20]
                raise ValueError('No explicitly labeled raw_audio channel pair found')
            chosen=min(waves,key=lambda i:i.filename);stem=Path(chosen.filename).stem
            selected=[i for i in entries if Path(i.filename).stem==stem and any('/'+k+'/' in i.filename for k in ['raw_audio','audio','accel','force','position'])]
            for item in selected:
                if item.file_size>8*1024*1024:raise ValueError('Trial member exceeds 8 MiB')
                raw=z.read(item);category=next(k for k in ['raw_audio','audio','accel','force','position'] if '/'+k+'/' in item.filename)
                name=category+'-'+Path(item.filename).name
                (a.out/name).write_bytes(raw)
                row={'archive_path':item.filename,'local_name':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                if name.endswith('.wav'):
                    import soundfile as sf
                    with sf.SoundFile(io.BytesIO(raw)) as audio:row.update({'rate':audio.samplerate,'channels':audio.channels,'frames':audio.frames,'seconds':len(audio)/audio.samplerate,'subtype':audio.subtype})
                else:
                    lines=raw.decode('utf-8-sig').splitlines();row.update({'lines':len(lines),'first_lines':lines[:6]})
                report['samples'].append(row)
            report['status']='representative_paired_trial_inspected' if len(selected)>=4 else 'partial_trial_inspected'
            report['channel_warning']='Raw audio channels are contact microphone and machine-noise reference, NOT binaural left/right. Processed audio has noise cancellation.'
    except Exception as e:report['error']=str(e)[:600]
    report['receipts']=f.receipts;report['downloaded_bytes']=f.used
    (a.out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'report':str(a.out/'report.json')}))
if __name__=='__main__':main()
