#!/usr/bin/env python3
"""Verify and summarize an inspected paired trial; never fit or replay it.

The raw WAV contains a contact microphone and a machine-noise reference,
not two ears. CSV logging intervals do not establish sensor bandwidth.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.signal import welch
import soundfile as sf


def summarize(folder):
    record=json.loads((folder/'report.json').read_text())
    if record['status']!='representative_paired_trial_inspected':
        raise ValueError('A complete paired trial inspection is required')
    result={'schema':'paired-trial-summary/1','source_doi':record['doi'],'license':record['license'],
            'archive':{k:record['archive'][k] for k in ['id','name','size','computed_md5']},
            'calibrates_ku100':False,'used_for_runtime_excitation':False,
            'channel_definition':'raw 0: contact + machine noise; raw 1: machine reference; processed: noise-cancelled mono',
            'sensor_bandwidth_warning':'Observed logging intervals are not independent force acquisition bandwidth. The paper describes an 80 Hz force converter.',
            'members':[]}
    for source in record['samples']:
        name=source['local_name']
        if Path(name).name!=name:raise ValueError('Unexpected member path')
        path=folder/name;digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=source['sha256']:raise ValueError('Source hash mismatch')
        row={k:source[k] for k in ['archive_path','local_name','bytes','sha256']}
        if path.suffix=='.wav':
            audio,rate=sf.read(path,dtype='float64',always_2d=True)
            if not np.isfinite(audio).all():raise ValueError('Nonfinite audio')
            freq,power=welch(audio,rate,nperseg=8192,axis=0,detrend='constant')
            total=power[(freq>=20)&(freq<20000)].sum(axis=0)
            row.update({'rate':rate,'frames':len(audio),'channels':audio.shape[1],
                        'peak_absolute':np.max(abs(audio),axis=0).tolist(),
                        'rms':np.sqrt(np.mean(audio**2,axis=0)).tolist(),
                        'pcm16_endpoint_samples':np.sum((audio<=-1)|(audio>=32767/32768),axis=0).tolist(),
                        'audible_band_power_fractions':{f'{lo}-{hi}':(power[(freq>=lo)&(freq<hi)].sum(axis=0)/np.maximum(total,1e-300)).tolist()
                          for lo,hi in [(20,250),(250,500),(500,2000),(2000,8000),(8000,20000)]}})
        else:
            data=np.genfromtxt(path,delimiter=',',names=True);times=data['time'];dt=np.diff(times)
            if not np.all(dt>0):raise ValueError('Non-increasing sensor timestamps')
            row.update({'columns':list(data.dtype.names),'rows':len(data),'first_time_s':float(times[0]),'last_time_s':float(times[-1]),
                        'median_logging_interval_s':float(np.median(dt)),
                        'nominal_rows_per_second_from_median_interval':float(1/np.median(dt))})
            if 'force' in data.dtype.names:
                unchanged=np.diff(data['force'])==0
                row.update({'force_mean_n':float(np.mean(data['force'])),
                            'identical_adjacent_force_fraction':float(np.mean(unchanged)),
                            'observed_value_changes_per_second':float(np.sum(~unchanged)/(times[-1]-times[0]))})
        result['members'].append(row)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    report=summarize(a.folder);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(a.out)
