"""Binaural surface-radiation *approximation*, not a calibrated BEM microphone solve.

Actual deforming-mesh normal flux is grouped on six rest faces. Each derivative
is treated as a compact monopole layer contribution at its projected direction on
an actually measured KU100 radius. Near-source scattering and hand occlusion are
not solved. There is no source clip, stochastic audio layer or loudness automation.
"""
from __future__ import annotations
import math
import numpy as np
from scipy import signal
from .binaural import BinauralMicrophone, require_binaural, BANK_SHA256

def render_surface_sound(result,rate,gain=1.):
    flux=np.asarray(result['flux'],float);scene=result['scene'];cap=scene['microphone'];duration=scene['duration_s']
    if flux.shape!=(round(duration*rate),6) or not np.isfinite(flux).all() or not math.isfinite(gain) or not 0<=gain<=1e8:raise ValueError('Invalid surface source')
    taps,beta=signal.kaiserord(100,4000/(rate/2));taps+=taps%2==0
    fir=signal.firwin(taps, min(16000,rate*.4),fs=rate,window=('kaiser',beta))
    q=signal.resample_poly(flux,1,rate//48000,axis=0,window=fir) if rate>48000 else flux.copy()
    # Centered derivative is an OFFLINE source operator, declared rather than a
    # causal real-time claim. Below-grid tails and low frequency drift are not noise.
    dq=np.gradient(q,1/48000,axis=0)*1.204/(4*np.pi)
    dq=signal.sosfilt(signal.butter(3,30,fs=48000,btype='high',output='sos'),dq,axis=0)
    mesh=result['mesh'];faces=mesh['faces'];groups=mesh['groups'];centroids=mesh['rest'][faces].mean(axis=1)
    az=np.deg2rad(cap['azimuth_deg']);r=cap['radius_m'];center=np.array([r*np.cos(az),r*np.sin(az),0.])
    # Local x axis follows azimuthal tangent; local y radial, local z vertical.
    rotation=np.array([[-np.sin(az),np.cos(az),0],[np.cos(az),np.sin(az),0],[0,0,1]])
    contributions=[];reports=[]
    for group in range(6):
        offset=centroids[groups==group].mean(axis=0);position=center+rotation@offset
        direction=float(np.rad2deg(np.arctan2(position[1],position[0])))
        cfg={'model':'KU100_NF','radius_m':r,'azimuth_knots_deg':[[0.,direction],[duration,direction]]}
        with BinauralMicrophone(cfg,duration,source_domain='surface_flux_derivative_proxy') as receiver:y,rep=receiver.render(dq[:,group])
        contributions.append(y);reports.append({'group':group,'rest_centroid_local_m':offset.tolist(),'projected_azimuth_deg':direction,'receiver':rep})
    y=np.sum(contributions,axis=0)*gain
    if abs(y).max()>=1:raise ValueError('Listening gain clips; no hidden limiter')
    # The full receiver tail is retained. No independently normalized ears.
    report={'schema':'solid-surface-audio/1','source':'deforming surface-normal flux derivative','readout':'uncalibrated monopole-layer approximation','source_groups':reports,
      'ku100_bank_sha256':BANK_SHA256,'full_frames':len(y),'gain':gain,'output_rate':48000,'stereo':require_binaural(y) if abs(y).max()>1e-10 else None,
      'source_recording_read':False,'contact_force_is_not_capsule_pressure':True,'pressure_calibrated':False,'absolute_radiation_validated':False,'human_listening_accepted':None,
      'limits':['Six centroid sources approximate surface radiation; no acoustic boundary element solve','Centers project onto the measured horizontal ring; no claimed near-contact HRTF','No hand acoustic occlusion, self-contact or wet seal','Input geometry/material-contact prediction remains bounded by measured refinement results','30 Hz high-pass and centered time derivative are explicit offline operations, not added pressure sensation']}
    return y,report
