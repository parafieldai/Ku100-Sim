import unittest
import numpy as np
from dataclasses import replace
from ku100sim.pressure_capture import CaptureConfig,capture_pressure

class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.rate=192000;self.t=np.arange(self.rate)/self.rate
 def tone(self,f=1000,rms=.02):
  a=np.sqrt(2)*rms*np.sin(2*np.pi*f*self.t);return np.column_stack([a,a*.5])
 def test_calibrated_1khz_chain(self):
  y,m=capture_pressure(self.tone(),self.rate)
  rms=np.sqrt(np.mean(y[12000:36000]**2,axis=0))
  expected=np.array([.02,.01])*.02*100/(2*np.sqrt(2))
  np.testing.assert_allclose(rms,expected,rtol=5e-4,atol=1e-7)
  self.assertFalse(m['device_calibrated']);self.assertLessEqual(m['quantization_max_error'],m['quantization_step']/2+1e-12)
 def test_dc_pressure_relaxes(self):
  y,_=capture_pressure(np.ones((self.rate,2))*.01,self.rate)
  self.assertLess(abs(y[-1000:]).max(),1e-7)
 def test_zero_pressure_is_zero(self):
  y,_=capture_pressure(np.zeros((self.rate,2)),self.rate);self.assertFalse(np.any(y))
 def test_mirror(self):
  a,_=capture_pressure(self.tone(),self.rate);b,_=capture_pressure(self.tone()[:,::-1],self.rate)
  np.testing.assert_array_equal(a,b[:,::-1])
 def test_low_cut_reduces_low_frequency_not_a_force_map(self):
  x=self.tone(50);a,_=capture_pressure(x,self.rate);b,_=capture_pressure(x,self.rate,replace(CaptureConfig(),optional_low_cut_hz=150))
  self.assertLess(np.linalg.norm(b[12000:36000])/np.linalg.norm(a[12000:36000]),.12)
 def test_virtual_antialias(self):
  y,_=capture_pressure(self.tone(30000),self.rate)
  self.assertLess(abs(y[12000:36000]).max(),2e-6)
 def test_overload_is_not_hidden(self):
  with self.assertRaises(ValueError):capture_pressure(self.tone(rms=2),self.rate)
 def test_invalid_inputs(self):
  for x in [np.zeros(20),np.full((10,2),np.nan),np.zeros((0,2)),np.zeros((10,3))]:
   with self.assertRaises(ValueError):capture_pressure(x,self.rate)
  for key,value in [('bits',True),('sensitivity_v_per_pa_at_1khz',float('nan')),('pressure_equalization_hz',-5),('preamp_gain_db',10**1000)]:
   with self.assertRaises(ValueError):capture_pressure(self.tone(),self.rate,replace(CaptureConfig(),**{key:value}))
if __name__=='__main__':unittest.main()
