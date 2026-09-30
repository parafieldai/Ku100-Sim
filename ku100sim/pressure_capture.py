"""Illustrative Pa -> volts -> ideal PCM chain, NOT a measured KU100 circuit.

Input must already be pressure at each capsule in Pa, not hand force F/A and
not the uncalibrated texture generator's digital output. Geometry/contact
transfer, microphone self-noise and analog overload are deliberately omitted.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy import signal

@dataclass(frozen=True)
class CaptureConfig:
    sensitivity_v_per_pa_at_1khz: float = .020
    preamp_gain_db: float = 40.
    adc_full_scale_peak_v: float = 2.*math.sqrt(2.)
    pressure_equalization_hz: float = 5.
    optional_low_cut_hz: float = 0.
    bits: int = 24
    output_rate: int = 48000

def _finite_number(x,lo,hi):
    try:return type(x) in (int,float) and math.isfinite(x) and lo<=x<=hi
    except OverflowError:return False

def capture_pressure(pressure_pa, input_rate:int, config:CaptureConfig=CaptureConfig()):
    """Simulate a declared linear capture chain, refusing overload or implicit gain.

    A one-pole equalization high-pass is normalized at 1 kHz before applying
    the nominal sensitivity. The optional two-pole low-cut is a GENERIC filter,
    not an identified KU100 filter circuit. resample_poly supplies numerical
    anti-aliasing and a centered FIR; this offline function is not causal ADC
    hardware emulation. Quantization is ideal, deterministic and undithered.
    """
    if not isinstance(config,CaptureConfig):raise ValueError('Expected CaptureConfig')
    if type(input_rate) is not int or input_rate not in (96000,192000,384000,768000):
        raise ValueError('Use an oversampled virtual pressure input')
    if type(config.output_rate) is not int or config.output_rate!=48000:
        raise ValueError('This diagnostic exports 48 kHz')
    if type(config.bits) is not int or config.bits not in (16,24):raise ValueError('Use 16 or 24 PCM bits')
    for key,lo,hi in [('sensitivity_v_per_pa_at_1khz',1e-6,1.),('preamp_gain_db',-20,80),
                      ('adc_full_scale_peak_v',.1,30.),('pressure_equalization_hz',.1,100),('optional_low_cut_hz',0,1000)]:
        if not _finite_number(getattr(config,key),lo,hi):raise ValueError('Invalid '+key)
    x=np.asarray(pressure_pa,dtype=float)
    if x.ndim!=2 or x.shape[1]!=2 or not 1<=len(x)<=input_rate*30 or not np.isfinite(x).all():
        raise ValueError('Expected finite stereo pressure, at most 30 seconds')
    if abs(x).max()>200:raise ValueError('Pressure exceeds this linear diagnostic range')
    sos=signal.butter(1,config.pressure_equalization_hz,fs=input_rate,btype='high',output='sos')
    gain_1k=abs(signal.sosfreqz(sos,worN=[1000],fs=input_rate)[1][0])
    dynamic=signal.sosfilt(sos,x,axis=0)/gain_1k
    if config.optional_low_cut_hz:
        dynamic=signal.sosfilt(signal.butter(2,config.optional_low_cut_hz,fs=input_rate,btype='high',output='sos'),dynamic,axis=0)
    mic=dynamic*config.sensitivity_v_per_pa_at_1khz
    preamp=mic*10**(config.preamp_gain_db/20.)
    scaled=preamp/config.adc_full_scale_peak_v
    if abs(scaled).max()>=1:raise ValueError('Capture overload: reduce gain or physical pressure; no limiter applied')
    # Explicit 20 kHz passband / 24 kHz stopband design; the generic short
    # resample_poly window was insufficient for the declared alias test.
    taps,beta=signal.kaiserord(100.,4000./(input_rate/2.))
    taps += (taps % 2 == 0)
    anti_alias=signal.firwin(taps,22000.,fs=input_rate,window=('kaiser',beta))
    full=signal.resample_poly(scaled,1,input_rate//config.output_rate,axis=0,window=anti_alias)
    step=1./2**(config.bits-1)
    if full.max()>1-step/2 or full.min()<-1+step/2:raise ValueError('Reconstruction overshoot reaches ADC full scale')
    code=np.rint(full*2**(config.bits-1)).astype(np.int32)
    pcm=code.astype(float)/2**(config.bits-1)
    report={'schema':'illustrative-capture/1','configuration':asdict(config),'input_unit':'Pa at capsule',
       'device_calibrated':False,'analog_circuit_identified':False,'contact_force_inferred':False,
       'output_frames':len(pcm),'input_peak_pa':np.max(abs(x),axis=0).tolist(),
       'microphone_output_peak_v':np.max(abs(mic),axis=0).tolist(),
       'preamp_output_peak_v':np.max(abs(preamp),axis=0).tolist(),
       'normalized_output_peak':np.max(abs(pcm),axis=0).tolist(),
       'quantization_max_error':float(abs(pcm-full).max()),'quantization_step':step,
       'noise_and_dither':'not modeled','normalization_or_limiting':False,
       'virtual_anti_aliasing':'centered Kaiser FIR via resample_poly; offline, not an ADC circuit model'}
    return pcm,report
