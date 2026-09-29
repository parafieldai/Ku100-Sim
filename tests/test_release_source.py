"""Independently assembled linear reference, energy and source-control ablations."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
from scipy.linalg import expm
ROOT=Path(__file__).resolve().parents[1]
class ReleaseSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.folder=Path(cls.tmp.name);cls.binary=cls.folder/'probe'
        subprocess.run(['g++','-std=c++17','-O3','-I',str(ROOT/'native'),str(ROOT/'tests/release_probe.cpp'),'-o',str(cls.binary)],check=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_case(self,mode='sealed',rate=384000):
        path=self.folder/f'{mode}-{rate}.f64'
        values=np.fromstring(subprocess.check_output([str(self.binary),mode,str(rate),str(path)],text=True),sep=' ')
        return values,np.fromfile(path,dtype=np.float64)
    def test_linear_state_against_matrix_exponential(self):
        rho,c,mu,V,r,l=1.204,343,1.81e-5,.8e-6,.0012,.002
        C=V/(rho*c*c);L=rho*l/(np.pi*r*r);R=8*mu*(l+.0001)/(np.pi*r**4);rr=rho*c/(4*np.pi*r*r);tau=r/c
        A=np.array([[0,-1/C,0],[1/L,-(R+rr)/L,rr/L],[0,1/tau,-1/tau]])
        exact=expm(A*.002)@np.array([80.,0,0]);weights=np.sqrt([C,L,rr*tau]);errors=[]
        for rate in [192000,384000,768000]:
            got=np.fromstring(subprocess.check_output([str(self.binary),'linear',str(rate)],text=True),sep=' ')
            errors.append(float(np.linalg.norm((got[:3]-exact)*weights)/np.linalg.norm(exact*weights)))
            self.assertLess(abs(got[3]),1e-17)
        self.assertLess(errors[-1],.005)
        self.assertGreater(errors[0]/errors[1],3.5);self.assertGreater(errors[1]/errors[2],3.5)
    def test_passivity_finite_and_supported_small_signal_regime(self):
        for mode in ['sealed','vented','slow']:
            with self.subTest(mode=mode):
                v,x=self.run_case(mode);self.assertTrue(np.isfinite(x).all());self.assertGreater(v[1],0)
                self.assertLess(v[0]/v[1],1e-8);self.assertGreaterEqual(v[2],0);self.assertGreaterEqual(v[3],0)
                self.assertLess(v[4]/101325,.05);self.assertLess(v[5],.05);self.assertLess(v[6],1000)
    def test_no_wall_motion_no_sound_and_no_stored_energy(self):
        v,x=self.run_case('silence');self.assertTrue(np.all(x==0));self.assertTrue(np.all(v==0))
    def test_venting_prevents_pressure_storage_and_suppresses_burst(self):
        v,a=self.run_case();w,b=self.run_case('vented')
        self.assertLess(w[4],v[4]*.01);self.assertLess(np.linalg.norm(b),np.linalg.norm(a)*.1)
    def test_slow_opening_changes_waveform_without_waveform_assets(self):
        _,a=self.run_case();_,b=self.run_case('slow')
        self.assertGreater(np.linalg.norm(a-b)/np.linalg.norm(a),.2)
    def test_release_temporal_refinement_and_determinism(self):
        _,a=self.run_case();_,replay=self.run_case();self.assertTrue(np.array_equal(a,replay))
        _,fine=self.run_case(rate=768000)
        relative=np.linalg.norm(a-fine[1::2])/np.linalg.norm(fine[1::2]);self.assertLess(relative,.005)
if __name__=='__main__':unittest.main()
