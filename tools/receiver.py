"""Extract a measured SOFA response without relabeling channels or modifying timing.
No wet-contact recording is used as runtime source. Requires numpy and h5py.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib
import h5py
import numpy as np

def extract(sofa: pathlib.Path, azimuth: int, output: pathlib.Path):
    if output.exists(): raise FileExistsError(output)
    with h5py.File(sofa,'r') as f:
        fs=float(f['Data.SamplingRate'][0]); positions=f['SourcePosition'][...]
        assert fs==48000 and f['Data.IR'].shape[1:]==(2,128)
        hits=np.flatnonzero(np.isclose(positions[:,0],azimuth)&np.isclose(positions[:,1],0))
        if len(hits)!=1: raise ValueError('Exactly one measured horizontal direction required')
        index=int(hits[0]);radius=float(positions[index,2])
        gains={.25:1.,.5:.330,.75:.250,1.:.160,1.5:.095}
        if radius not in gains:raise ValueError('Distance not covered by authors gain correction')
        ir=f['Data.IR'][index].T
        if np.any(f['Data.Delay'][...]):raise ValueError('Nonzero SOFA delay requires explicit implementation')
        def text(v):
            if not isinstance(v,bytes): return str(v)
            try: return v.decode('utf-8')
            except UnicodeDecodeError: return v.decode('latin-1')
        attrs={k:text(v) for k,v in f.attrs.items()}
        receiver_positions=f['ReceiverPosition'][...].tolist()
    output.parent.mkdir(parents=True,exist_ok=True)
    np.savetxt(output,ir*gains[radius],fmt='%.17g',header='SOFA raw receiver order; shared distance correction applied exactly once')
    meta={'source':'https://zenodo.org/records/4297951','author_gain_note':'https://audiogroup.web.th-koeln.de/FILES/NF_Datasets_Gains_infos.pdf','sofa_sha256':hashlib.sha256(sofa.read_bytes()).hexdigest(),'fir_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'source_index':index,'azimuth_deg':azimuth,'distance_m':radius,'distance_gain_applied':gains[radius],'sample_rate':48000,'taps':128,'receiver_positions':receiver_positions,'attributes':attrs,'scope':'Measured airborne response, not a measured contact path. Raw channel order retained; lateral cues must be checked independently. Common absolute flight time is not reconstructed.'}
    output.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('sofa',type=pathlib.Path);p.add_argument('--azimuth',type=int,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();extract(a.sofa,a.azimuth,a.out)
