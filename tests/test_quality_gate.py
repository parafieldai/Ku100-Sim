import importlib.util
from pathlib import Path
import unittest
import numpy as np
spec=importlib.util.spec_from_file_location('quality_gate',Path(__file__).resolve().parents[1]/'scripts/quality_gate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class QualityTests(unittest.TestCase):
    def test_silence_does_not_prove_bandwidth(self):
        a=np.zeros((48000,2));r=m.compare(a,a,48000)
        self.assertFalse(r['all_bands_verified']);self.assertTrue(all(s=='unassessed-weak-excitation' for b in r['bands'] for s in b['status']))
    def test_bad_quiet_ear_cannot_hide_in_combined_energy(self):
        t=np.arange(48000)/48000;y=np.stack([np.sin(2*np.pi*100*t),.001*np.sin(2*np.pi*100*t)],axis=1);x=y.copy();x[:,1]*=.5
        r=m.compare(x,y,48000);self.assertEqual(r['bands'][0]['status'],['pass','fail'])
        self.assertAlmostEqual(r['bands'][0]['relative_l2'][1],.5,places=10)
    def test_known_broadband_error_is_measured_without_level_fitting(self):
        y=np.random.default_rng(17).normal(size=(48000,2));r=m.compare(y*1.02,y,48000)
        self.assertFalse(r['all_bands_verified']);self.assertTrue(all(s=='fail' for b in r['bands'] for s in b['status']))
        for b in r['bands']:np.testing.assert_allclose(b['relative_l2'],.02,atol=1e-10)
    def test_equal_broadband_and_invalid_input(self):
        y=np.random.default_rng(7).normal(size=(48000,2));self.assertTrue(m.compare(y,y,48000)['all_bands_verified'])
        with self.assertRaises(ValueError):m.compare(y,y[:5],48000)
    def test_sub_audio_energy_is_not_misreported_as_audible_timbre(self):
        from ku100sim.audio import describe
        t=np.arange(48000)/48000
        a=np.stack([1+0.01*np.sin(2*np.pi*1000*t),2+0.001*np.sin(2*np.pi*1000*t)],axis=1)
        report=describe(48000,a)
        self.assertGreater(report['sub_20hz_fraction_of_total_power'][0],.999)
        np.testing.assert_allclose(report['audible_band_energy_fractions']['500_2000_hz'],[1,1],atol=1e-12)
        np.testing.assert_allclose(report['dc_sample_mean'],[1,2],atol=1e-12)
if __name__=='__main__':unittest.main()
