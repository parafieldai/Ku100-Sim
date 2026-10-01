"""Reusable compact-source radiation for already-ringing linear modal graphs.

This is a narrowband, quasi-static research path, NOT an exact KU100 digital
 twin or a broadband contact renderer. A rigid sphere supplies source-to-ear
pressure propagation; a measured KU100 monopole response anchors the correction
at 0.25 m. That correction is frozen with range. Closer predictions are unmeasured.
No object name selects the algorithm, and no performance audio is read.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import numpy as np
from .binaural import BANK_SHA256, RATE, require_binaural

C = 343.0
EAR_DIRECTIONS = np.array([[0., 1., 0.], [0., -1., 0.]])


def _number(x, lo, hi, name):
    try:
        good = type(x) in (int, float) and math.isfinite(x) and lo <= x <= hi
    except OverflowError:
        good = False
    if not good:
        raise ValueError('Invalid ' + name)
    return float(x)


def _xyz(values, name):
    try:
        a = np.asarray(values, dtype=float)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError('Invalid ' + name) from e
    if a.ndim != 2 or a.shape[1] != 3 or not 1 <= len(a) <= 100000 or not np.isfinite(a).all():
        raise ValueError('Finite bounded (N,3) ' + name + ' required')
    return a


def sphere_green(frequency, sources, *, radius=.0875, directions=EAR_DIRECTIONS, extra_terms=0):
    """e^(+i wt) Green function on a rigid sphere surface, excluding 1/(4*pi).

    Stable Hankel RATIO recurrence avoids low-frequency/high-order overflow.
    G = conjugate[-sum((2n+1) h_n(kr)/h'_n(ka) P_n(mu))/(k*a*a)].
    Units 1/m, source outside sphere. This solves an IDEAL sphere, not pinnae.
    """
    f = _number(frequency, .1, 8000., 'frequency')
    a = _number(radius, .001, .2, 'sphere radius')
    if type(extra_terms) is not int or not 0 <= extra_terms <= 128:
        raise ValueError('Invalid refinement')
    s = _xyz(sources, 'source positions')
    ears = _xyz(directions, 'receiver directions')
    if not np.allclose(np.linalg.norm(ears, axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError('Unit receiver directions required')
    r = np.linalg.norm(s, axis=1)
    if np.min(r-a) < .005 or np.max(r) > 10:
        raise ValueError('Source must be at least 5 mm outside sphere and within 10 m')
    k = 2*np.pi*f/C; z = k*a; zs = k*r
    nmax = max(int(np.ceil(z+4*np.cbrt(z)+20)), int(np.ceil(np.log(1e-15)/np.log(a/r.min())))) + extra_terms
    if nmax > 768:
        raise ValueError('Expansion budget exceeded')
    mu = np.clip((s/r[:,None]) @ ears.T, -1, 1)
    hratio = a/r*np.exp(1j*(zs-z))
    total = (hratio/(1j-1/z))[:,None]*np.ones_like(mu)
    p0 = np.ones_like(mu); p1 = mu.copy()
    ra = 1/z-1j; rs = 1/zs-1j
    for n in range(1,nmax+1):
        if n > 1:
            ra = (2*n-1)/z - 1/ra
            rs = (2*n-1)/zs - 1/rs
        hratio *= rs/ra
        ratio = hratio/(1/ra-(n+1)/z)
        pn = p1 if n == 1 else ((2*n-1)*mu*p1-(n-1)*p0)/n
        total += (2*n+1)*ratio[:,None]*pn
        if n > 1:
            p0,p1 = p1,pn
    result = np.conjugate(-total/(k*a*a))
    if not np.isfinite(result).all():
        raise FloatingPointError('Nonfinite spherical field')
    return result


def placed_sources(center, angle_deg, elements):
    """Rigid pose of a signed monopole array, x forward/y left/z up."""
    c = _xyz(center, 'center positions')
    e = np.asarray(elements, float)
    angle = np.asarray(angle_deg, float)
    if e.ndim != 2 or e.shape[1] != 4 or not 1 <= len(e) <= 16 or not np.isfinite(e).all():
        raise ValueError('Use 1-16 [x,y,z,signed_weight] elements')
    if np.linalg.norm(e[:,:3],axis=1).max() > .04 or abs(e[:,3]).max()>4:
        raise ValueError('Array exceeds compact-source bounds')
    if angle.shape != (len(c),) or not np.isfinite(angle).all() or abs(angle).max()>36000:
        raise ValueError('Invalid orientation trajectory')
    theta=np.deg2rad(angle);co=np.cos(theta);si=np.sin(theta)
    out=np.repeat(c[:,None,:],len(e),axis=1)
    out[:,:,0] += co[:,None]*e[None,:,0]-si[:,None]*e[None,:,1]
    out[:,:,1] += si[:,None]*e[None,:,0]+co[:,None]*e[None,:,1]
    out[:,:,2] += e[None,:,2]
    return out, e[:,3]


def array_free_field(frequency, center, angle_deg, elements, receivers):
    """Exact finite monopole sum in free field; separately useful for tests."""
    f = _number(frequency,.1,8000,'frequency')
    sources,w=placed_sources(center,angle_deg,elements)
    receivers=_xyz(receivers,'receivers')
    distances=np.linalg.norm(sources[:,:,None,:]-receivers[None,None,:,:],axis=-1)
    if distances.min()<.005:raise ValueError('Receiver too close to source element')
    return np.sum(w[None,:,None]*np.exp(-2j*np.pi*f/C*distances)/distances,axis=1)


class CompactRadiation:
    """One parameterized propagation operator for signed compact source arrays.

    Anchored mode: measured KU100 response at the same center direction, divided
    by a unit-monopole sphere prediction at that anchor, then multiplied by the
    finite-source sphere prediction. It does not stack two complete HRTFs.
    Range-frozen pinna/capsule correction is a hypothesis below measured ranges.
    """
    def __init__(self, *, radius=.0875, bank_path=None):
        self.radius=_number(radius,.065,.11,'head radius')
        path=Path(bank_path) if bank_path else Path(__file__).resolve().parents[1]/'data/ku100_bank.bin'
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=1843264:
            raise ValueError('Verified KU100 bank required')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=BANK_SHA256:
            raise ValueError('Wrong receiver bank')
        self.bank=np.frombuffer(raw,dtype='<f4',offset=64).reshape(5,360,2,128)[0].astype(float)

    def measured_anchor(self,frequency,azimuth):
        f=_number(frequency,64,4000,'modal frequency')
        azimuth=np.atleast_1d(np.asarray(azimuth,float))
        if azimuth.ndim!=1 or not np.isfinite(azimuth).all():raise ValueError('Invalid azimuth')
        angle=np.mod(azimuth,360);a0=np.floor(angle).astype(int)%360;w=angle-np.floor(angle)
        # Same common propagation and fixed 31-sample latency as existing receiver.
        phasor=np.exp(-2j*np.pi*f*np.arange(128)/RATE)
        H=self.bank@phasor
        response=H[a0]*(1-w[:,None])+H[(a0+1)%360]*w[:,None]
        return response*np.exp(-2j*np.pi*f*(.25/C+31/RATE))

    def response(self,frequency,center,angle_deg,elements,*,extra_terms=0):
        f=_number(frequency,64,4000,'modal frequency')
        center=_xyz(center,'center positions')
        if abs(center[:,2]).max()>1e-12:
            raise ValueError('Measured anchor supports horizontal source centers only')
        r=np.linalg.norm(center,axis=1)
        if r.min()<self.radius+.025 or r.max()>1.5:
            raise ValueError('Center gap 25 mm to sphere and maximum range 1.5 m required')
        sources,weights=placed_sources(center,angle_deg,elements)
        g=sphere_green(f,sources.reshape(-1,3),radius=self.radius,extra_terms=extra_terms)
        field=np.sum(g.reshape(len(center),len(weights),2)*weights[None,:,None],axis=1)
        anchor=center*(.25/r)[:,None]
        ref=sphere_green(f,anchor,radius=self.radius,extra_terms=extra_terms)
        az=np.rad2deg(np.arctan2(center[:,1],center[:,0]))
        if abs(ref).min()<1e-8:raise ValueError('Ill-conditioned anchoring')
        return self.measured_anchor(f,az)*field/ref


def render_radiated(engine, config):
    """Free-ring modal source from the EXISTING SimulationEngine, two-ear output.

    Bounded narrowband rendering, valid for slowly changing geometry and slow
    decay. Force/contact/nonlinear graphs are refused, not approximated silently.
    No new physical object solver and no stored waveform is involved.
    """
    if not isinstance(config,dict) or set(config)!={'schema','head_radius_m','center_knots','angle_knots_deg','mode_elements','control_rate_hz'} or config['schema']!='compact-modal-radiation/1':
        raise ValueError('Invalid radiation configuration')
    if engine.frame or not engine.exact or np.any(engine.params[:,6]):
        raise ValueError('Fresh uncoupled linear free-ring engine required')
    for curves,waves in engine.controls:
        if any(np.any(c[:,1]) for c in curves) or waves:
            raise ValueError('This narrowband path handles free ringing, not driven/contact attacks')
    ctrl=config['control_rate_hz']
    if type(ctrl) is not int or ctrl not in (120,240,480,960):raise ValueError('Unsupported pose rate')
    centers=np.asarray(config['center_knots'],float)
    angles=np.asarray(config['angle_knots_deg'],float)
    T=engine.duration
    for k,cols in ((centers,4),(angles,2)):
        if k.ndim!=2 or k.shape[1]!=cols or len(k)<2 or len(k)>64 or not np.isfinite(k).all() or k[0,0]!=0 or k[-1,0]!=T or np.any(np.diff(k[:,0])<=0):
            raise ValueError('Knots must cover the exact scene duration')
    # Trajectory interpolation is intentionally LINEAR: constant slow rotation,
    # not ease-in/out at every angle. Corner speeds remain below this bound.
    if np.max(np.linalg.norm(np.diff(centers[:,1:],axis=0),axis=1)/np.diff(centers[:,0]))>.1:
        raise ValueError('Translation exceeds 0.1 m/s quasi-static bound')
    if np.max(abs(np.diff(angles[:,1])/np.diff(angles[:,0])))>180:
        raise ValueError('Rotation exceeds 180 deg/s quasi-static bound')
    mapping=config['mode_elements'];ids=[n['id'] for n in engine.scene['nodes']]
    if not isinstance(mapping,dict) or set(mapping)!=set(ids):raise ValueError('Supply source elements for each mechanical node')
    nframes=round(T*RATE);sample_t=np.arange(1,nframes+1)/RATE
    pt=np.linspace(0,T,round(T*ctrl)+1)
    xyz=np.column_stack([np.interp(pt,centers[:,0],centers[:,i]) for i in (1,2,3)])
    deg=np.interp(pt,angles[:,0],angles[:,1])
    operator=CompactRadiation(radius=config['head_radius_m'])
    params=engine.params;decay=params[:,3]/(2*params[:,0]);omegas=np.sqrt(params[:,1]/params[:,0]-decay**2)
    frequencies=omegas/(2*np.pi)
    if not np.isfinite(frequencies).all() or frequencies.min()<64 or frequencies.max()>4000 or np.any(decay/(2*np.pi*frequencies)>.01):
        raise ValueError('Outside narrowband free-ring scope')
    response=[operator.response(float(f),xyz,deg,mapping[id]) for f,id in zip(frequencies,ids)]
    q=np.empty((nframes,engine.n));v=np.empty_like(q)
    take=engine.rate//RATE;at=0
    while engine.frame<round(T*engine.rate):
        count=min(4096,round(T*engine.rate)-engine.frame)
        # Both supported internal rates divide 4096; last block divisible too.
        block=engine.process(count);b=block[take-1::take]
        q[at:at+len(b)]=b[:,:engine.n];v[at:at+len(b)]=b[:,engine.n:2*engine.n];at+=len(b)
    if at!=nframes:raise RuntimeError('Internal/output clock mismatch')
    y=np.zeros((nframes,2));mode_reports=[]
    r=np.linalg.norm(xyz,axis=1)
    # Common envelope flight delay; source pose and head scatter are quasi-static.
    # Differential path phase is in the complex Green function. This is NOT a
    # broadband causal transient boundary-element solution.
    delay=np.interp(sample_t,pt,r/C+31/RATE)
    for j,(f,omega,alpha,H) in enumerate(zip(frequencies,omegas,decay,response)):
        zq=q[:,j]-1j*(v[:,j]+alpha*q[:,j])/omega
        zv=(-alpha+1j*omega)*zq
        # Acoustic source acceleration, with a stated relative coupling weight.
        # Not a measured surface-volume map; absolute Pa is NOT inferred.
        za=(-alpha+1j*omega)*zv*engine.weights[j]
        # Exact transport of a free modal carrier to fractional time; avoids
        # linear interpolation damping the upper mode. H already carries the
        # carrier propagation phase. Restore only the envelope decay in flight.
        transported=za*np.exp(alpha*delay)
        transported[sample_t<delay]=0
        for ear in range(2):
            h=np.interp(sample_t,pt,H[:,ear].real)+1j*np.interp(sample_t,pt,H[:,ear].imag)
            y[:,ear]+=np.real(transported*h)
        mode_reports.append({'node_id':ids[j],'frequency_hz':float(f),'decay_per_s':float(alpha),'elements':mapping[ids[j]],'response_real':H.real.tolist(),'response_imag':H.imag.tolist()})
    if not np.isfinite(y).all():raise FloatingPointError('Nonfinite rendered output')
    # Recording begins after initial mechanical state. Fixed playback-only fades
    # are declared, never described as modeled mallet strikes or final contact.
    fade=round(.02*RATE);outfade=min(round(.2*RATE),nframes//4)
    y[:fade]*=(.5-.5*np.cos(np.linspace(0,np.pi,fade)))[:,None]
    y[-outfade:]*=(.5+.5*np.cos(np.linspace(0,np.pi,outfade)))[:,None]
    report={'schema':'compact-modal-radiation-result/1','kernel_sha256':engine.kernel_sha256,
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bank_sha256':BANK_SHA256,
        'model':'rigid-sphere compact-array prediction with 0.25 m measured KU100 anchor',
        'output_domain':'uncalibrated_binaural_acoustic_prediction','measured_device_geometry':False,
        'measured_at_rendered_range':False,'absolute_pressure_calibrated':False,'haptic_output':False,
        'recording_input':False,'human_listening_assessed':False,'waveform_fragments_replayed':False,
        'pose_t_s':pt.tolist(),'center_xyz_m':xyz.tolist(),'orientation_deg':deg.tolist(),
        'minimum_center_gap_m':float(r.min()-operator.radius),'head_radius_m':operator.radius,
        'mode_reports':mode_reports,'playback_fades_s':[.02,outfade/RATE],
        'stereo':require_binaural(y) if np.any(y) else None,
        'initial_energy_j':float(np.sum(.5*params[:,0]*params[:,9]**2+.5*params[:,1]*params[:,8]**2)),
        'final_energy_j':float(block[-1,-4]),'dissipation_j':float(block[-1,-2]),
        'energy_balance_error_j':float(block[-1,-1]),
        'limitations':['Rigid sphere is not measured KU100 pinna/head geometry',
            'Frozen measured anchor correction is extrapolative at close distances; no newly measured near-contact HRTF',
            'Compact signed monopoles approximate modal radiation; no fitted fork mesh, radiation backreaction or stem contact',
            'Bank extension below approximately 200 Hz is analytic, not a measured low-frequency pressure reference',
            'Narrowband free-ring and quasi-static pose; not a broadband transient/Doppler/contact solution',
            'No skin, bone-conduction or pressure-occlusion/tactile actuator model',
            'Higher modes, fork loading and source coupling are illustrative, not identified from an actual fork']}
    return y,report
