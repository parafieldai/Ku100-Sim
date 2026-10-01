"""Independent equations and intervention tests, NOT ASMR listening scores."""
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from scipy import signal,special
from ku100sim.unified import SimulationEngine
from ku100sim.compact_radiation import CompactRadiation,sphere_green,array_free_field,placed_sources


def scene(seconds=.1,freq=256):
    return {'schema':'shared-mechanics/1','name':'arbitrary resonator', 'duration_s':seconds,'internal_rate':192000,
        'nodes':[{'id':'q','mass_kg':.002,'k2_n_m':.002*(2*np.pi*freq)**2,
        'damping_n_s_m':.0008,'limit_m':.001,'initial':{'q_m':1e-5,'v_m_s':0}}],
        'evidence':{'status':'unmeasured_reduced_model','limits':'numerical experiment'}}


def config(seconds=.1,rotation=5):
    return {'schema':'compact-modal-radiation/1','head_radius_m':.0875,
        'center_knots':[[0,0,-.12,0],[seconds,0,-.12,0]],'angle_knots_deg':[[0,0],[seconds,rotation]],
        'mode_elements':{'q':[[-.016,0,0,1],[-.006,0,0,-1],[.006,0,0,-1],[.016,0,0,1]]},'control_rate_hz':240}


class RadiationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.operator=CompactRadiation()
    def test_sphere_independent_bessel_reference(self):
        for f in (128,512,3200):
            src=np.array([[0,-.25,0],[.2,.05,0]])
            d=np.linalg.norm(src,axis=1);a=.0875;k=2*np.pi*f/343;n=np.arange(65)
            H=special.spherical_jn(n[:,None],k*d)+1j*special.spherical_yn(n[:,None],k*d)
            Hp=special.spherical_jn(n,k*a,True)+1j*special.spherical_yn(n,k*a,True)
            mu=src[:,1]/d
            expected=[]
            for sign in (1,-1):
                p=special.eval_legendre(n[:,None],sign*mu)
                expected.append(np.conj(-np.sum((2*n+1)[:,None]*H/Hp[:,None]*p,axis=0)/(k*a*a)))
            np.testing.assert_allclose(sphere_green(f,src),np.array(expected).T,rtol=1e-11,atol=1e-11)
    def test_surface_neumann_boundary_independent(self):
        # Independently evaluate incident + scattered series off the surface.
        f=512;k=2*np.pi*f/343;a=.0875;r=.2;n=np.arange(50);mu=.4
        hs=special.spherical_jn(n,k*r)+1j*special.spherical_yn(n,k*r)
        ja=special.spherical_jn(n,k*a,True)
        ha=special.spherical_jn(n,k*a,True)+1j*special.spherical_yn(n,k*a,True)
        def pressure(x):
            j=special.spherical_jn(n,k*x);h=j+1j*special.spherical_yn(n,k*x)
            return 1j*k*np.sum((2*n+1)*hs*(j-ja/ha*h)*special.eval_legendre(n,mu))
        eps=1e-6;gradient=(pressure(a+eps)-pressure(a-eps))/(2*eps)
        self.assertLess(abs(gradient)/abs(pressure(a)),1e-7)
    def test_near_series_convergence(self):
        src=np.array([[0,-.1025,0],[.01,-.1175,0]])
        for f in (64,128,512,4000):
            a=sphere_green(f,src);b=sphere_green(f,src,extra_terms=50)
            np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-10)
    def test_static_limit(self):
        d=.12;a=.0875
        expected=np.array([sum((2*n+1)/(n+1)*(a/d)**n*special.eval_legendre(n,c) for n in range(200))/d for c in (-1,1)])
        x=sphere_green(.1,[[0,-d,0]])[0]
        np.testing.assert_allclose(abs(x),expected,rtol=1e-6)
    def test_small_sphere_freefield(self):
        f=128;s=np.array([[.1,-.3,0]])
        actual=sphere_green(f,s,radius=.001)
        expected=np.exp(-2j*np.pi*f/343*np.linalg.norm(s[0]))/np.linalg.norm(s[0])
        self.assertLess(np.max(abs(actual-expected))/abs(expected),.006)
    def test_pinned_anchor_matches_existing_fir(self):
        from tests.test_binaural import independent_filter
        for f in (128,256,512,3000):
            for angle in (-90,12.5,90):
                h=independent_filter(angle)
                ref=h@np.exp(-2j*np.pi*f*np.arange(h.shape[1])/48000)
                np.testing.assert_allclose(self.operator.measured_anchor(f,[angle])[0],ref,rtol=3e-5,atol=1e-7)
    def test_unit_monopole_anchor_identity(self):
        c=np.array([[0,-.25,0],[.25,0,0],[0,.25,0]])
        a=self.operator.response(512,c,np.zeros(3),[[0,0,0,1]])
        b=self.operator.measured_anchor(512,[-90,0,90])
        np.testing.assert_allclose(a,b,rtol=1e-13,atol=1e-13)
    def test_quadrupole_small_spacing_analytic(self):
        f=426;k=2*np.pi*f/343;h=.0002;theta=np.linspace(0,2*np.pi,500,endpoint=False);r=.2
        detector=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.zeros(len(theta))])
        p=array_free_field(f,[[0,0,0]],[0],[[-h,0,0,1],[0,0,0,-2],[h,0,0,1]],detector)[0]/h**2
        c=np.cos(theta)
        ref=np.exp(-1j*k*r)/r*(-k*k*c*c+(3*c*c-1)*(1j*k/r+1/r**2))
        self.assertLess(np.linalg.norm(p-ref)/np.linalg.norm(ref),3e-6)
    def test_near_four_far_two_lobes(self):
        theta=np.linspace(0,2*np.pi,720,endpoint=False);f=426
        for r,expected in ((.05,4),(2.,2)):
            pts=np.column_stack([r*np.cos(theta),r*np.sin(theta),np.zeros(len(theta))])
            p=abs(array_free_field(f,[[0,0,0]],[0],[[-.016,0,0,1],[-.006,0,0,-1],[.006,0,0,-1],[.016,0,0,1]],pts)[0])
            count=len(signal.find_peaks(np.tile(p,3),prominence=p.max()*1e-3)[0])
            # Count one complete periodic interior only.
            peaks=signal.find_peaks(np.tile(p,3),prominence=p.max()*1e-3)[0]
            self.assertEqual(np.sum((peaks>=720)&(peaks<1440)),expected)
    def test_superposition_and_monopole_rotation_invariance(self):
        c=np.array([[0,-.12,0],[0,-.25,0]]);angle=np.array([12.,54.]);a=[[-.012,0,0,1],[.012,0,0,-1]]
        p=self.operator.response(256,c,angle,a)
        parts=sum(self.operator.response(256,c,angle,[e]) for e in a)
        np.testing.assert_allclose(p,parts,atol=1e-12)
        np.testing.assert_allclose(self.operator.response(256,c,angle,[[0,0,0,1]]),self.operator.response(256,c,angle+90,[[0,0,0,1]]))
    def test_radiation_rotates_without_moving_center(self):
        phi=np.arange(0,361,5.);c=np.repeat([[0,-.1175,0]],len(phi),axis=0)
        h=self.operator.response(256,c,phi,config()['mode_elements']['q'])
        self.assertGreater(np.ptp(20*np.log10(abs(h[:,1]))),15)
    def test_asymmetric_side_has_distinct_ears(self):
        x=self.operator.response(256,[[0,-.1175,0]],[0],config()['mode_elements']['q'])
        self.assertGreater(abs(x[0,1]),abs(x[0,0])*2)
    def test_invalid_geometries_refused(self):
        for pos in ([[0,-.095,0]],[[0,-.25,.01]]):
            with self.assertRaises(ValueError):self.operator.response(256,pos,[0],[[0,0,0,1]])
        with self.assertRaises(ValueError):sphere_green(512,[[0,-.088,0]])
        with self.assertRaises(ValueError):sphere_green(512,[[0,-.25,0]],extra_terms=-1)
    def test_shared_engine_and_metadata_invariance(self):
        sc=scene();cfg=config()
        with SimulationEngine(sc) as e:a,r=e.render_radiated(cfg)
        sc['name']='not a fork, no algorithm dispatch'
        with SimulationEngine(sc) as e:b,_=e.render_radiated(cfg)
        np.testing.assert_array_equal(a,b)
        self.assertFalse(r['stereo']['identical_channels']);self.assertFalse(r['absolute_pressure_calibrated'])
        self.assertFalse(r['haptic_output']);self.assertLess(abs(r['energy_balance_error_j']),1e-15)
    def test_zero_is_silent_without_ambient(self):
        sc=scene();sc['nodes'][0]['initial']['q_m']=0
        with SimulationEngine(sc) as e:y,_=e.render_radiated(config())
        self.assertFalse(np.any(y))
    def test_nonlinear_or_forced_source_is_not_silently_approximated(self):
        sc=scene();sc['nodes'][0]['k4_n_m3']=1e5
        with SimulationEngine(sc) as e:
            with self.assertRaises(ValueError):e.render_radiated(config())
        sc=scene();sc['nodes'][0]['driver']={'force':[[0,1],[.1,0]]}
        with SimulationEngine(sc) as e:
            with self.assertRaises(ValueError):e.render_radiated(config())
    def test_audio_reads_rejected_during_new_render(self):
        real_open=io.open;attempts=[]
        def guarded(file,*a,**kw):
            if isinstance(file,(str,Path)) and str(file).lower().endswith(('.wav','.mp3','.flac','.npy','.ogg')):
                attempts.append(str(file));raise AssertionError('Recording read')
            return real_open(file,*a,**kw)
        with SimulationEngine(scene()) as e:
            with patch('io.open',guarded),patch('builtins.open',guarded),patch('numpy.load',side_effect=AssertionError('array read')):
                y,_=e.render_radiated(config())
        self.assertEqual(attempts,[]);self.assertTrue(np.any(y))
    def test_static_ring_matches_existing_measured_receiver(self):
        from ku100sim.binaural import BinauralMicrophone
        sc=scene(2.);cfg=config(2.,0)
        cfg['center_knots']=[[0,0,-.25,0],[2,0,-.25,0]]
        cfg['mode_elements']={'q':[[0,0,0,1]]}
        with SimulationEngine(sc) as e:y,_=e.render_radiated(cfg)
        p=sc['nodes'][0];alpha=p['damping_n_s_m']/(2*p['mass_kg']);w=np.sqrt(p['k2_n_m']/p['mass_kg']-alpha*alpha)
        t=np.arange(1,96001)/48000;s0=-alpha+1j*w
        z=p['initial']['q_m']*(1-1j*alpha/w)*np.exp(s0*t)
        src=np.real(s0*s0*z)
        config_old={'model':'KU100_NF','radius_m':.25,'azimuth_knots_deg':[[0,-90],[2,-90]]}
        with BinauralMicrophone(config_old,2,source_domain='numerical_test') as mic:old,_=mic.render(src)
        start,end=4800,72000
        self.assertLess(np.linalg.norm(y[start:end]-old[start:end])/np.linalg.norm(old[start:end]),.0005)

    def test_pose_interpolation_refinement(self):
        sc=scene(.5);c=config(.5,75)
        with SimulationEngine(sc) as e:a,_=e.render_radiated(c)
        c['control_rate_hz']=480
        with SimulationEngine(sc) as e:b,_=e.render_radiated(c)
        self.assertLess(np.linalg.norm(a-b)/np.linalg.norm(b),.001)

if __name__=='__main__':unittest.main()
