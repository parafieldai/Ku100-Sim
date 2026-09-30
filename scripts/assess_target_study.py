#!/usr/bin/env python3
"""Expose target failures separately from test/build success. No realism percentage."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]

def assess(study):
    lookup={x['id']:x for x in study['candidates']};refs={x['id']:x for x in study['references']}
    rows=[]
    for comp in study['comparisons']:
        ref=refs[comp['reference']];candidate=lookup[comp['candidate']];ear=0 if ref['side_label']=='left' else 1
        rows.append({'reference':ref['id'],'candidate':candidate['id'],
           'ild_error_db':comp['ild_error_db'],
           'near_1_to_4khz_fraction_reference':ref['metrics']['band_power_fraction_per_ear'][ear][2],
           'near_1_to_4khz_fraction_candidate':candidate['metrics']['band_power_fraction_per_ear'][ear][2],
           'relative_band_error_db_per_ear':comp['relative_band_power_error_db_per_ear'],
           'detected_peak_rate_error_hz':comp['detected_peak_rate_error_hz']})
    return {'schema':'target-readiness/1','assessment_completed':True,'target_accepted':False,
      'requirements':[
        {'requirement':'Fresh waveform, no runtime recording retrieval','status':'implemented for the empirical comparator; not a physical realism pass'},
        {'requirement':'Observed target action/source identity','status':'unresolved; chapter labels and waveform alone are insufficient'},
        {'requirement':'Tongue/ear contact, rolling, peel, release and wet history','status':'not implemented by this comparator or validated in the generic fixture'},
        {'requirement':'Calibrated bilateral contact transmission','status':'not established'},
        {'requirement':'Prediction of unseen physical actions/conditions','status':'not established; test crops previously inspected'},
        {'requirement':'Reference-relevant listening acceptance','status':'not performed; no prefilled ratings'}],
      'comparisons':rows,
      'failure_interpretation':'Right-side aggregate separation improves relative to the generic fixture, but spectrum is wrong and the left-profile transfer across the selected excerpts fails. The continuous negative control can also score well on a single descriptor. This source is not accepted as the target simulator.',
      'publication_status':'Comparison tool may be published as a research study; the target simulator may not be advertised as complete.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,default=ROOT/'web/target/generated/study.json');p.add_argument('--out',type=Path,default=ROOT/'validation/local/target-readiness.json');p.add_argument('--require-target',action='store_true');a=p.parse_args()
    r=assess(json.loads(a.study.read_text()));r['study_sha256']=hashlib.sha256(a.study.read_bytes()).hexdigest();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'assessment_completed':True,'target_accepted':False,'report':str(a.out)}))
    if a.require_target:p.exit(2,'Target acceptance is NOT established. This is an expected failing product gate, not a passed simulation.\n')
