import copy,io,json,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy import linalg,signal
from ku100sim.modal_object import *

class ModalObjectTests(unittest.TestCase):
    def model(self):
        return {'schema':SCHEMA,'sample_rate':RATE,'calibrated_force_to_pressure':False,'modes':[[733.,9.,.11,.2],[1870.,25.,-.07,.08]]}
    def test_iir_equals_analytical_damped_response(self):
        m=self.model();direct=impulse_response(m,.15);recursive=render(m,[(0.,1.,0.)],.15)
        self.assertLess(float(np.linalg.norm(recursive-direct)/np.linalg.norm(direct)),1e-10)
    def test_mode_against_independent_matrix_exponential_and_energy(self):
        f,d,c,s=self.model()['modes'][0];w=2*np.pi*f;omega2=w*w+d*d
        A=np.array([[0.,1.],[-omega2,-2*d]])
        state=np.array([0.,1.]);step=linalg.expm(A/RATE);samples=[];energies=[]
        for _ in range(3000):
            samples.append((w*s+d*c)*state[0]+c*state[1]);energies.append((omega2*state[0]**2+state[1]**2)/2);state=step@state
        t=np.arange(3000)/RATE;expected=np.exp(-d*t)*(c*np.cos(w*t)+s*np.sin(w*t))
        np.testing.assert_allclose(samples,expected,atol=1e-13,rtol=1e-9)
        self.assertLessEqual(float(np.max(np.diff(energies))),1e-14)
    def test_zero_and_impulse_scaling(self):
        m=self.model();self.assertFalse(render_hybrid(m,[],1.).any())
        a=render(m,[(.2,.5,.0002)],1.);b=render(m,[(.2,1.,.0002)],1.)
        np.testing.assert_array_equal(2*a,b)
    def test_pulse_equals_convolution(self):
        m=self.model();n=round(.0004*RATE);pulse=np.sin(np.pi*(np.arange(n)+.5)/n);pulse/=pulse.sum()
        expected=signal.convolve(impulse_response(m,1.),pulse)[:RATE]
        np.testing.assert_allclose(render(m,[(0.,1.,.0004)],1.),expected,atol=1e-12)
    def test_no_file_or_reference_access_during_generation(self):
        model=self.model()
        with patch('builtins.open',side_effect=AssertionError('file read')),patch('numpy.load',side_effect=AssertionError('NPY recording read')):
            self.assertTrue(np.isfinite(render_hybrid(model,[(.1,1.,.0001)],1.)).all())
    def test_reject_bad_model_and_actions(self):
        for value in [float('nan'),-1.,25000.]:
            m=self.model();m['modes'][0][0]=value
            with self.assertRaises(ValueError):validate(m)
        m=self.model();m['samples']=[0.]
        with self.assertRaises(ValueError):validate(m)
        for events in [[(0.,-1.,.0001)],[(.999,1.,.004)],[(True,1.,0.)],None]:
            with self.assertRaises(ValueError):render(self.model(),events,1.)
        for x in [np.zeros(RATE*2),np.zeros(20)]:
            with self.assertRaises(ValueError):crop_measurement(x)
        with self.assertRaises(ValueError):metrics(np.zeros(10),np.ones(10))
    def test_silence_does_not_establish_quality(self):
        with self.assertRaises(ValueError):metrics(np.zeros(100),np.zeros(100))
    def test_fit_recovers_synthetic_modes(self):
        target=impulse_response(self.model(),2.)
        fitted=fit_modes(target,2)
        got=np.sort(np.array(fitted['modes'])[:,0])
        np.testing.assert_allclose(got,[733.,1870.],atol=1.)
        self.assertLess(fitted['fit']['relative_waveform_residual'],.08)
    def test_profiles_bounded_and_distinct(self):
        roots=Path(__file__).resolve().parents[1]/'models/object-profiles'
        files=sorted(roots.glob('*.json'));self.assertEqual(len(files),3)
        responses=[]
        for f in files:
            self.assertLess(f.stat().st_size,50000);m=json.loads(f.read_text());validate(m)
            self.assertFalse(m['provenance']['original_ear_recordings_used'])
            with patch('builtins.open',side_effect=AssertionError('recording read')):
                a=render_hybrid(m,[(.1,1.,.00008)],1.,seed=9010)
                b=render_hybrid(m,[(.1,1.,.00008)],1.,seed=9010)
                c=render_hybrid(m,[(.1,1.,.00008)],1.,seed=9011)
            np.testing.assert_array_equal(a,b)
            if 'residual' in m:self.assertFalse(np.array_equal(a,c))
            responses.append(a)
        self.assertFalse(np.array_equal(responses[0],responses[1]))
        self.assertFalse(np.array_equal(responses[1],responses[2]))
if __name__=='__main__':unittest.main()
