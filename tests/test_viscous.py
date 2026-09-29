"""Independent analytical and work-identity tests, not a recording-realism rating."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
from scipy.special import ive, jn_zeros
ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
#include "viscous.hpp"
#include <iostream>
#include <iomanip>
int main(int argc,char** argv){
 double radius=argc>1?std::stod(argv[1]):.003, fs=argc>2?std::stod(argv[2]):192000.;
 ku100::ViscousTube t(1.204,1.81e-5,radius,.18,.5/fs,true);
 std::cout<<std::setprecision(17)<<"{\"mass\":"<<t.mass<<",\"r0\":"<<t.steady_resistance<<",\"poles\":[";
 for(unsigned i=0;i<t.terms;i++)std::cout<<(i?",":"")<<t.lambda[i];
 std::cout<<"],\"weights\":[";for(unsigned i=0;i<t.terms;i++)std::cout<<(i?",":"")<<t.resistance[i];
 double work=0,loss=0,error=0;
 for(unsigned i=0;i<20000;i++){
  double pressure=i<10000?.13*std::sin(.003*i)+.03*std::cos(.43*i):0;
  double mid=(pressure+t.bias())/t.impedance;
  work+=pressure*mid/fs;loss+=t.advance(mid)/fs;
  error=std::max(error,std::abs(t.energy()+loss-work));
 }
 std::cout<<"],\"work\":"<<work<<",\"loss\":"<<loss<<",\"energy\":"<<t.energy()<<",\"max_residual\":"<<error<<"}";
}
'''
class ViscousTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.p=Path(cls.tmp.name);(cls.p/'probe.cpp').write_text(PROBE)
  subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-I',str(ROOT/'native'),str(cls.p/'probe.cpp'),'-o',str(cls.p/'probe')],check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def probe(self,r=.003,fs=192000):return json.loads(subprocess.check_output([str(self.p/'probe'),str(r),str(fs)],text=True))
 def test_impedance_against_exact_bessel_function(self):
  # Independent continuous no-slip solution, not the grouped eigenvalue sum.
  for radius in [.0005,.001,.003,.01]:
   p=self.probe(radius);s=2j*np.pi*np.geomspace(20,20000,1001);z=radius*np.sqrt(s*1.204/1.81e-5)
   exact=1.204*.18/(np.pi*radius**2)*s*ive(0,z)/ive(2,z)
   approx=p['mass']*s+p['r0']+sum(w*s/(s+l) for w,l in zip(p['weights'],p['poles']))
   self.assertLess(float(np.max(abs(approx-exact)/abs(exact))),.0003)
   self.assertLess(float(np.max(abs(approx.real-exact.real)/exact.real)),.004)
 def test_low_frequency_inertance_and_poiseuille(self):
  p=self.probe();m=1.204*.18/(np.pi*.003**2)
  self.assertAlmostEqual(p['r0'],8*1.81e-5*.18/(np.pi*.003**4),places=8)
  self.assertAlmostEqual((p['mass']+sum(w/l for w,l in zip(p['weights'],p['poles'])))/m,4/3,places=12)
 def test_positive_real_and_memory_energy(self):
  p=self.probe();self.assertTrue(all(v>0 for v in p['poles']+p['weights']))
  self.assertGreaterEqual(p['loss'],0);self.assertGreaterEqual(p['energy'],0)
  self.assertLess(p['max_residual']/max(abs(p['work']),1e-30),1e-10)
 def test_grouped_coefficients_reproduce_bessel_zeros(self):
  p=self.probe();zeros=jn_zeros(2,8192);edges=np.unique(np.r_[np.arange(9),np.round(np.geomspace(8,8192,25)).astype(int)])
  scale=1.81e-5/(1.204*.003**2);base=1.204*.18/(np.pi*.003**2)
  for k,(i,j) in enumerate(zip(edges[:-1],edges[1:])):
   self.assertAlmostEqual(p['poles'][k]/scale,1/np.mean(1/zeros[i:j]**2),delta=1e-7)
   self.assertAlmostEqual(p['weights'][k]/(base*scale),4*(j-i),places=7)
 def test_passivity_at_coarse_and_fine_steps(self):
  for fs in [48000,384000,768000]:
   p=self.probe(fs=fs);self.assertLess(p['max_residual']/max(abs(p['work']),1e-30),1e-10)

if __name__=='__main__':unittest.main()
