"""Receiver equation checks, not human ASMR acceptance tests."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy import signal
from ku100sim.binaural import (ROOT,BANK_SHA256,BinauralMicrophone,default_microphone,
    validate_microphone,require_binaural,angles_at)


def config(angle=90,radius=.25,seconds=.05):
    return {'model':'KU100_NF','radius_m':radius,'azimuth_knots_deg':[[0,angle],[seconds,angle]]}


def independent_filter(angle,radius=.25):
    # Independent public wire-format decoder and delay construction, not native
    # HrirBank::at or native delay_signal. Radius gains are already in the bank.
    b=(ROOT/'data/ku100_bank.bin').read_bytes()
    bank=np.frombuffer(b,dtype='<f4',offset=64).reshape(5,360,2,128)
    ri=(.25,.5,.75,1.,1.5).index(radius)
    f=angle%360;a=int(np.floor(f))%360;w=f-np.floor(f)
    h=(1-w)*bank[ri,a].astype(float)+w*bank[ri,(a+1)%360].astype(float)
    delay=radius/343*48000;integer=int(delay);frac=delay-integer
    j=np.arange(63);window=np.i0(9*np.sqrt(np.maximum(0,1-((j-31)/31)**2)))/np.i0(9)
    v=np.sinc(j-31-frac)*window;v/=v.sum()
    return np.stack([np.pad(signal.convolve(v,ear),(integer,0)) for ear in h])


class BinauralTests(unittest.TestCase):
    def setUp(self):self.x=np.random.default_rng(23).normal(0,.002,2400)
    def render(self,x=None,c=None,block=2048):
        x=self.x if x is None else x;c=config() if c is None else c
        with BinauralMicrophone(c,len(x)/48000,source_domain='numerical_test') as m:return m.render(x,block)
    def test_pinned_bank(self):
        self.assertEqual(hashlib.sha256((ROOT/'data/ku100_bank.bin').read_bytes()).hexdigest(),BANK_SHA256)
    def test_static_against_independent_fir_full_tail(self):
        for angle in (90,-90,15.5,-1e-15):
            y,r=self.render(c=config(angle))
            h=independent_filter(angle)
            ref=np.stack([np.convolve(self.x,z) for z in h],axis=1)
            np.testing.assert_allclose(y,ref,atol=2e-16,rtol=2e-12)
            self.assertEqual(len(y),len(self.x)+223)
            self.assertEqual(r['full_filter_tail_frames'],223)
    def test_radius_gain_not_applied_twice(self):
        for radius in (.5,1.,1.5):
            y,_=self.render(c=config(radius=radius));h=independent_filter(90,radius)
            ref=np.stack([np.convolve(self.x,z) for z in h],axis=1)
            np.testing.assert_allclose(y,ref,atol=3e-16,rtol=2e-12)
    def test_measured_channel_orientation(self):
        left,_=self.render(c=config(90));right,_=self.render(c=config(-90))
        self.assertGreater(np.linalg.norm(left[:,0]),np.linalg.norm(left[:,1])*3)
        self.assertGreater(np.linalg.norm(right[:,1]),np.linalg.norm(right[:,0])*3)
        lag=lambda a:signal.correlation_lags(len(a),len(a))[np.argmax(signal.correlate(a[:,1],a[:,0],method='fft'))]
        self.assertGreater(lag(left),10);self.assertLess(lag(right),-10)
    def test_moving_against_independent_output_time_fir(self):
        c=config(10);c['azimuth_knots_deg']=[[0,10],[.05,11]]
        y,r=self.render(c=c)
        t=np.maximum(0,np.arange(len(y))/48000-r['propagation_delay_s']-r['fractional_delay_processing_latency_s'])
        z=np.clip(t/.05,0,1);phi=10+z**3*(10-15*z+6*z*z)
        padded=np.pad(self.x,(223,223));expected=np.zeros_like(y)
        for n,angle in enumerate(phi):
            h=independent_filter(angle)
            expected[n]=h@padded[n:n+224][::-1]
        np.testing.assert_allclose(y,expected,atol=3e-16,rtol=3e-11)
    def test_block_size_invariance_moving(self):
        c=config(10);c['azimuth_knots_deg']=[[0,10],[.05,11]]
        a,_=self.render(c=c,block=73);b,_=self.render(c=c,block=2048)
        np.testing.assert_array_equal(a,b)
    def test_azimuth_wrap_is_continuous(self):
        a,_=self.render(c=config(-1e-15));b,_=self.render(c=config(360))
        np.testing.assert_array_equal(a,b)
    def test_zero_is_zero_not_added_ambience(self):
        y,r=self.render(x=np.zeros(2400));self.assertFalse(np.any(y))
        with self.assertRaises(ValueError):require_binaural(y)
    def test_no_mono_export(self):
        for x in (np.column_stack([self.x,self.x]),np.column_stack([self.x,np.zeros(len(self.x))])):
            with self.assertRaises(ValueError):require_binaural(x)
        y,_=self.render();self.assertFalse(require_binaural(y)['identical_channels'])
    def test_fileless_processing_after_receiver_init(self):
        with BinauralMicrophone(config(),.05,source_domain='numerical_test') as mic:
            with patch('builtins.open',side_effect=AssertionError('file read')),patch('numpy.load',side_effect=AssertionError('file read')):
                y,r=mic.render(self.x)
        self.assertEqual(len(y),2623)
    def test_wrong_3dio_or_contact_scope_rejected(self):
        for field,value in [('model','3Dio'),('radius_m',.01),('radius_m',.3)]:
            c=config();c[field]=value
            with self.assertRaises(ValueError):validate_microphone(c,.05)
        c=config();c['wetness']=1
        with self.assertRaises(ValueError):validate_microphone(c,.05)
        with self.assertRaises(ValueError):BinauralMicrophone(config(),.05,source_domain='calibrated_pa')
    def test_corrupt_bank_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bank.bin';p.write_bytes((ROOT/'data/ku100_bank.bin').read_bytes()[:-1]+b'Z')
            with self.assertRaises(ValueError):BinauralMicrophone(config(),.05,source_domain='numerical_test',bank_path=p)
    def test_bad_trajectory_or_fast_motion_refused(self):
        for knots in ([[0,0],[.05,180]],[[.01,90],[.05,90]],[[0,90],[0,80]],[[0,90],[.05,float('nan')]]):
            c=config();c['azimuth_knots_deg']=knots
            with self.assertRaises(ValueError):validate_microphone(c,.05)
    def test_invalid_block_does_not_advance(self):
        with BinauralMicrophone(config(),.05,source_domain='numerical_test') as m:
            for x in (np.full(12,np.nan),np.zeros((10,2)),np.zeros(2401)):
                with self.assertRaises(ValueError):m.process(x)
                self.assertEqual(m.frame,0)
    def test_finish_once_and_after_full_source(self):
        with BinauralMicrophone(config(),.05,source_domain='numerical_test') as m:
            with self.assertRaises(ValueError):m.finish()
            m.process(self.x);tail=m.finish();self.assertEqual(tail.shape,(223,2))
            with self.assertRaises(ValueError):m.finish()
            with self.assertRaises(ValueError):m.process([0.])
    def test_small_angle_boundary_no_switch_click(self):
        a,_=self.render(c=config(89.999));b,_=self.render(c=config(90.001))
        self.assertLess(np.linalg.norm(a-b)/np.linalg.norm(a),.001)
    def test_scene_name_does_not_dispatch_receiver(self):
        a,_=self.render();b,_=self.render();np.testing.assert_array_equal(a,b)
    def test_source_captured_coloration_not_hidden(self):
        with BinauralMicrophone(config(),.05,source_domain='effective_microphone_response') as m:
            _,r=m.render(self.x)
        self.assertTrue(r['original_source_capture_coloration_retained'])
        self.assertFalse(r['device_calibrated_absolute_pressure'])

if __name__=='__main__':unittest.main()
