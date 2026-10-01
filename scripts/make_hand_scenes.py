#!/usr/bin/env python3
"""Declared geometry and material/skin assumptions; no acoustic fit or clip input."""
import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def scene(kind='rub',cells=(6,3,4),rate=96000,duration=5.):
    material={'name':'Ecoflex 00-30: literature-informed reduced constitutive approximation','density_kg_m3':1070.,'mu_pa':json.loads((ROOT/'models/materials/ecoflex-compression.json').read_text())['mu_pa'],'bulk_pa':2000000.,'shear_viscosity_pa_s':.6,'bulk_viscosity_pa_s':.3,
      'memory':[{'mu_pa':190.,'tau_s':12.},{'mu_pa':125.,'tau_s':177.}],
      'provenance':{'density':'Smooth-On nominal product value','elastic':'Bounded ideal-compression approximation fitted to author CSV files 1-3 over 5-20 percent compression; files 4-5 evaluated separately. See models/materials/ecoflex-compression.json','relaxation':'Rounded shear-arm priors reflecting relative magnitudes and time constants in Roels Table 3; not full multiaxial fit','bulk_viscosity_friction':'Explicit unmeasured priors; no audio-band calibration'}}
    tips=[]
    for a,sign in enumerate((1,-1)):
        radius=.009 if a==0 else .010
        yfar=sign*(.004+radius+.0007);y=sign*(.004+radius-.0018);firm=sign*(.004+radius-.0023)
        x=-.004
        knots=[[0,x,yfar,0],[.3,x,yfar,0],[.7,x,y,0],[1.1,x,y,0],[2.0,.004 if a==0 else -.005,y,0],[2.4,.004 if a==0 else -.005,y,0],[3.25,-.004 if a==0 else -.002,y,0],[3.5,-.004 if a==0 else -.002,firm,0],[3.8,-.004 if a==0 else -.002,firm,0],[4.3,x,yfar,0],[5.,x,yfar,0]]
        if kind=='hold':
            for k in knots:k[1]=x
        if kind=='light':
            for k in knots:
                if abs(k[2])<abs(yfar):k[2]=sign*(.004+radius-.0007)
        if kind=='nocontact':
            for k in knots:k[2]=yfar
        tips.append({'id':'fingertip' if a==0 else 'thumb','mass_kg':.02,'radius_m':radius,'drive_stiffness_n_m':5000.,'drive_damping_n_s_m':12.,'skin_modulus_pa':60000.,'skin_layer_m':.002,'normal_viscosity_pa_s_m':60.,'tangential_stiffness_pa_m':20000000.,'mu_static':.8,'mu_dynamic':.45,'stribeck_speed_m_s':.0015,'target_knots':knots,
        'provenance':'Spherical translating fingertip with compliant skin layer; all contact/drive parameters are explicit priors, not an identified human hand'})
    if kind=='rate-neutral':
        for tip in tips:tip['mu_static']=tip['mu_dynamic']=.55
    if kind=='frictionless':
        for tip in tips:tip['mu_static']=tip['mu_dynamic']=0.
    if duration!=5.:
        for tip in tips:
            # Fast tests may cut the original trajectory; rescaling is not default.
            import numpy as np
            from ku100sim.solid_scene import trajectory
            ts=[k[0] for k in tip['target_knots'] if k[0]<duration]+[duration]
            ps,_=trajectory(tip['target_knots'],np.array(ts));tip['target_knots']=[[t,*p] for t,p in zip(ts,ps)]
    return {'schema':'coupled-solids/1','name':{'rub':'Pinch, rub, reverse, squeeze and release','hold':'Pinch and hold: no lateral rubbing','light':'Light pinch and rubbing','frictionless':'Same hand path, tangential friction removed','nocontact':'Same hand path, no contact','rate-neutral':'Same hand path, rate-independent friction prior'}[kind],
      'duration_s':duration,'internal_rate':rate,'solid':{'geometry':{'type':'tetrahedral_box','size_m':[.034,.008,.024],'cells':list(cells)},'material':material,'support':'clamped_x_min','volume_formulation':'averaged_nodal'},'fingertips':tips,
      'microphone':{'model':'KU100_NF','radius_m':.25,'azimuth_deg':-75.},
      'evidence':{'status':'research_prototype','target':'Dry skin-surrogate contact with solid silicone; no fluid','limits':'Not an anatomical hand or identified skin friction. Connected finite-volume tetrahedral geometry; explicit finite-strain contact. No water, liquid seal or bubbles. Audio uses approximate surface radiation and the measured airborne KU100 receiver, not direct ear-contact calibration.'}}

if __name__=='__main__':
    for kind in ['rub','light','hold','frictionless','nocontact','rate-neutral']:
        p=ROOT/'scenes/hand'/f'{kind}.json';p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(scene(kind),indent=2)+'\n')
