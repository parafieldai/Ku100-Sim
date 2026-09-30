#!/usr/bin/env python3
"""Describe source discrepancies without inventing listener or physical scores."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ku100sim.target_metrics import compare_stats

def assess(folder):
    m=json.loads((Path(folder)/'iteration.json').read_text())
    rows=[]
    for ref in m['reference_descriptors']:
        for source in m['samples']:
            if source['side']!=ref['side_label']:continue
            row=compare_stats(ref['metrics'],source['metrics'])
            ear=source['near_channel'];a=ref['metrics']['band_power_fraction_per_ear'][ear];b=source['metrics']['band_power_fraction_per_ear'][ear]
            row.update({'reference_id':ref['id'],'source_id':source['id'],
                'source_fitting_scope':source['generation'].get('fitting_scope','control_or_previous'),
                'same_excerpt_fitted':source['generation'].get('fitting_scope')=='reference_excerpt' and ref['id'] in ('chapter-03','chapter-04'),
                'near_ear_band_power_reference':a,'near_ear_band_power_generated':b,
                'near_ear_peak_rate_reference_hz':ref['metrics']['acoustic_peak_rate_hz'],
                'near_ear_peak_rate_generated_hz':source['metrics']['acoustic_peak_rate_hz']})
            rows.append(row)
    return {'schema':'source-iteration-assessment/1','target_accepted':False,
        'human_listening_performed':False,'physical_target_implemented':False,
        'scope':'Reference-guided examples test a representation on fitted excerpts. The range-fitted right source uses previously inspected excluded excerpts; none is claimed as new blind physical validation.',
        'comparisons':rows,'source_hashes':m['source_hashes'],
        'limitations':['Stationary statistics do not prescribe the original event order or gesture.',
            'The inter-ear shaper is common within this comparison, not a newly calibrated physical receiver.',
            'The phase control matches Fourier magnitudes before the common fade; post-fade finite-window spectra can differ.',
            'Source playback correctness and optimizer loss are not listener acceptance.']}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=ROOT/'web/source/generated');p.add_argument('--out',type=Path,default=ROOT/'validation/local/source-iteration.json');a=p.parse_args()
    r=assess(a.input);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps({'report':str(a.out),'comparisons':len(r['comparisons']),'target_accepted':False}))
