#!/usr/bin/env python3
"""Measured receiver evidence and stereo-only publication; no ASMR pass score."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.binaural import BinauralMicrophone,BANK_SHA256,require_binaural

def run():
    duration=.25;x=np.random.default_rng(734).normal(0,.002,round(duration*48000));rows=[]
    for azimuth in (90,-90):
        c={'model':'KU100_NF','radius_m':.25,'azimuth_knots_deg':[[0,azimuth],[duration,azimuth]]}
        with BinauralMicrophone(c,duration,source_domain='numerical_test') as receiver:
            y,r=receiver.render(x)
        lag=signal.correlation_lags(len(y),len(y))[np.argmax(signal.correlate(y[:,1],y[:,0],method='fft'))]
        r['xcorr_itd_right_minus_left_us']=float(lag/48000*1e6)
        assert r['xcorr_itd_right_minus_left_us']*azimuth>0
        assert r['stereo']['ild_l_minus_r_db']*azimuth>0
        rows.append(r)
    previews=[]
    for category in ('unified','objects'):
        root=ROOT/'web'/category/'generated';m=json.loads((root/'manifest.json').read_text())
        for row in m['samples']:
            path=root/row.get('audio',row.get('file'));rate,a=wavfile.read(path)
            scale=32768. if a.dtype==np.int16 else 1.
            metrics=require_binaural(a.astype(float)/scale)
            receiver=row['report']['receiver'] if 'report' in row else row['receiver']
            assert rate==48000 and receiver['bank_sha256']==BANK_SHA256
            assert receiver['output_frames']==len(a)
            previews.append({'category':category,'id':row['id'],'frames':len(a),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'metrics':metrics,'source_domain':receiver['source_domain'],'microphone':receiver['configuration']})
    return {'schema':'binaural-delivery-check/1','generated_utc':datetime.now(timezone.utc).isoformat(),
        'all_object_previews_have_distinct_ears':True,'preview_count':len(previews),'examples':previews,
        'measured_receiver_checks':rows,'bank_sha256':BANK_SHA256,'ASMR_listening_pass':None,
        'source_timbre_acceptance':'Not established. User rejected previous mono prototype character.',
        'source_material_calibrated':False,'direct_ear_contact_supported':False,
        'independent_test_suite':'tests/test_binaural.py; static/moving FIR, tails, actual ear order, block state and no-mono guard'}

if __name__=='__main__':
    out=ROOT/'validation/local/binaural';out.mkdir(parents=True,exist_ok=True)
    report=run();(out/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'distinct_binaural_previews':report['preview_count'],'ASMR_listening_pass':None}))
