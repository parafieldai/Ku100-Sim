"""Independent component checks and bounded contact trajectories, not ASMR scores."""
import copy, json, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from ku100sim.unified import SimulationEngine
from ku100sim.solid_scene import box_mesh, build_library, ptr, iptr, trajectory, validate
from scripts.make_hand_scenes import scene

class MaterialTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.lib,_=build_library()
 def probe(self,F,Fd=None,p=None):
  F=np.ascontiguousarray(F,dtype=float);Fd=np.zeros((3,3)) if Fd is None else np.ascontiguousarray(Fd,dtype=float)
  p=np.array([52596.,2e6,0.,0.,0.,12.,0.,177.] if p is None else p,float);out=np.empty(11)
  result=self.lib.solid_material(ptr(F),ptr(Fd),ptr(p),ptr(out))
  if result: raise ValueError(self.lib.solid_error().decode())
  return out[0],out[1],out[2:].reshape(3,3)
 def test_stress_is_independent_energy_gradient(self):
  F=np.array([[.98,.07,.01],[-.02,1.03,0.],[0.,.01,1.01]])
  e,_,P=self.probe(F);g=np.zeros((3,3));h=1e-6
  for i in range(3):
   for j in range(3):
    A=F.copy();B=F.copy();A[i,j]+=h;B[i,j]-=h
    g[i,j]=(self.probe(A)[0]-self.probe(B)[0])/(2*h)
  np.testing.assert_allclose(P,g,rtol=2e-7,atol=2e-4)
 def test_rest_is_zero(self):
  e,d,P=self.probe(np.eye(3));self.assertAlmostEqual(e,0);self.assertAlmostEqual(d,0);np.testing.assert_allclose(P,0,atol=1e-10)
 def test_rotation_objectivity(self):
  a=.71;R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
  F=np.diag([.9,1.05,1.02]);Fd=np.array([[.01,.03,0.],[0,-.02,0],[.01,0,.01]])
  p=[52596.,2e6,.6,.3,190.,12.,125.,177.]
  e,d,P=self.probe(F,Fd,p);e2,d2,P2=self.probe(R@F,R@Fd,p)
  self.assertAlmostEqual(e,e2,places=8);self.assertAlmostEqual(d,d2,places=10);np.testing.assert_allclose(P2,R@P,rtol=1e-12,atol=1e-8)
 def test_rigid_rotation_rate_has_no_viscous_dissipation(self):
  W=np.array([[0,-3.,0],[3.,0,0],[0,0,0]])
  e,d,P=self.probe(np.eye(3),W,[52596.,2e6,.6,.3,0,12,0,177]);self.assertAlmostEqual(d,0,places=12)
 def test_viscous_work_and_nonnegative_dissipation(self):
  F=np.diag([.95,1.03,1.]);Fd=np.array([[.3,.2,0],[-.1,.4,.1],[0,.1,-.2]])
  _,_,P0=self.probe(F,Fd);_,d,P=self.probe(F,Fd,[52596.,2e6,.6,.3,0,12,0,177])
  self.assertGreater(d,0);self.assertAlmostEqual(float(np.sum((P-P0)*Fd)),d,places=8)
 def test_isochoric_uniaxial_difference(self):
  lam=.85;F=np.diag([lam,lam**-.5,lam**-.5]);_,_,P=self.probe(F)
  # Subtract the hydrostatic Lagrange multiplier needed for zero side traction.
  hydro=P[1,1]*F[1,1];nominal=P[0,0]-hydro/lam
  self.assertAlmostEqual(nominal,52596.*(lam-lam**-2),places=7)
 def test_invalid_volume_fails_instead_of_clamping(self):
  with self.assertRaises(ValueError): self.probe(np.diag([-.1,1,1]))

class AverageVolumeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.lib,_=build_library()
 def calc(self,J):
  x,t,*_=box_mesh([.02,.01,.015],[2,1,1]);v=np.ascontiguousarray(np.linalg.det((x[t[:,1:]]-x[t[:,:1]]).transpose(0,2,1))/6)
  out=np.empty(len(t)+1);J=np.ascontiguousarray(J,float)
  code=self.lib.solid_volume_probe(len(x),len(t),iptr(t),ptr(v),ptr(J),2e6,ptr(out));self.assertEqual(code,0)
  return out,v
 def test_nodal_volume_energy_derivative(self):
  J=np.linspace(.94,1.03,12);v,_=self.calc(J);g=[]
  for i in range(len(J)):
   a=J.copy();b=J.copy();a[i]+=1e-6;b[i]-=1e-6;g.append((self.calc(a)[0][0]-self.calc(b)[0][0])/2e-6)
  np.testing.assert_allclose(v[1:],g,rtol=2e-8,atol=1e-10)
 def test_homogeneous_volume_matches_exact_bulk_potential(self):
  r,v=self.calc(np.full(12,.95));self.assertAlmostEqual(r[0],.5*2e6*sum(v)*.05**2,places=12)
  np.testing.assert_allclose(r[1:],v*2e6*(-.05),rtol=1e-12,atol=1e-12)
 def test_zero_bulk_deformation_has_zero_pressure(self):
  r,v=self.calc(np.ones(12));np.testing.assert_allclose(r,0,atol=1e-12)

class GeometryTests(unittest.TestCase):
 def test_mesh_volume_orientation_and_closed_surface(self):
  size=[.034,.008,.024];x,t,f,a,g=box_mesh(size,[4,2,3]);V=np.linalg.det((x[t[:,1:]]-x[t[:,:1]]).transpose(0,2,1))/6
  self.assertTrue(np.all(V>0));self.assertAlmostEqual(float(V.sum()),float(np.prod(size)),places=14)
  av=.5*np.cross(x[f[:,1]]-x[f[:,0]],x[f[:,2]]-x[f[:,0]])
  np.testing.assert_allclose(av.sum(0),0,atol=1e-15);self.assertEqual(set(g),set(range(6)))
  self.assertTrue(np.all((av*x[f].mean(1)).sum(1)>0));self.assertAlmostEqual(float(a.sum()),2*(size[0]*size[1]+size[0]*size[2]+size[1]*size[2]),places=12)
 def test_driver_derivative_matches_finite_difference(self):
  knots=[[0,0,0,0],[1,.01,.02,0],[2,0,0,0]];t=np.array([.13,.5,.79,1.35]);h=1e-6
  p,v=trajectory(knots,t);num=(trajectory(knots,t+h)[0]-trajectory(knots,t-h)[0])/(2*h);np.testing.assert_allclose(v,num,atol=1e-10)
 def test_unsupported_water_and_unknown_controls_rejected(self):
  for field in ['wetness','water','air','pressure_boost']:
   s=scene(duration=.1);s[field]=1
   with self.assertRaises(ValueError):validate(s)
  s=scene(duration=.1);s['solid']['geometry']['type']='water_pouch'
  with self.assertRaises(ValueError):validate(s)
 def test_resolution_and_bad_parameters_rejected(self):
  s=scene(duration=.1);s['solid']['material']['mu_pa']=-1
  with self.assertRaises(ValueError):validate(s)
  s=scene(duration=.1);s['solid']['geometry']['cells']=[16,16,16]
  with self.assertRaises(ValueError):validate(s)
  s=scene(duration=.1);s['microphone']['radius_m']=.01
  with self.assertRaises(ValueError):validate(s)

class CoupledContactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=scene(cells=(4,2,3),duration=1.)
  with SimulationEngine(cls.scene) as e: cls.r=e.render(block_frames=512)
 def test_real_geometry_two_actors_and_contact_feedback(self):
  r=self.r;s=self.scene;n=len(r['mesh']['rest']);nv=n+2;b=r['trace'];p=b[:,1:1+3*nv].reshape(-1,nv,3)
  target,_=trajectory(s['fingertips'][0]['target_knots'],b[:,0])
  self.assertGreater(float(np.max(abs(p[:,-2]-target))),1e-5)
  self.assertGreater(min(r['report']['peak_normal_forces_n']),.05)
  self.assertGreater(r['report']['tetrahedra'],100)
  self.assertGreater(float(abs(p[:,:n]-r['mesh']['rest']).max()),1e-5)
 def test_clamped_support_and_positive_volume(self):
  r=self.r;x=r['mesh']['rest'];p=r['trace'][:,1:1+3*len(x)].reshape(-1,len(x),3);fixed=np.isclose(x[:,0],x[:,0].min())
  np.testing.assert_allclose(p[:,fixed],np.broadcast_to(x[fixed],p[:,fixed].shape),rtol=0,atol=0)
  self.assertGreater(r['report']['min_jacobian'],.9);self.assertLess(r['report']['max_jacobian'],1.1)
 def test_work_accounting_is_bounded_not_hidden(self):
  r=self.r['report'];self.assertGreater(r['actuator_work_j'],0);self.assertGreater(r['dissipation_j'],0)
  self.assertLess(r['balance_relative_to_net_work'],.01)
 def test_block_invariance_and_metadata_independence(self):
  s=copy.deepcopy(self.scene);s['name']='Not a material selector'
  with SimulationEngine(s) as e: other=e.render(block_frames=777)
  np.testing.assert_array_equal(self.r['flux'],other['flux']);np.testing.assert_array_equal(self.r['trace'],other['trace'])
 def test_rendering_does_not_load_recordings(self):
  s=scene(duration=.05)
  with SimulationEngine(s) as e:
   with patch('builtins.open',side_effect=AssertionError('File read')),patch('numpy.load',side_effect=AssertionError('Array read')):
    b=e.process(1024)
   self.assertTrue(np.isfinite(b).all())
 def test_silence_without_contact(self):
  s=scene(kind='nocontact',cells=(4,2,3),duration=.8)
  with SimulationEngine(s) as e:r=e.render()
  self.assertEqual(max(r['report']['peak_normal_forces_n']),0)
  self.assertLess(float(abs(r['flux']).max()),1e-13)
 def test_live_controls_require_consistent_pair(self):
  with SimulationEngine(scene(duration=.05)) as e:
   with self.assertRaises(ValueError):e.process(2,targets=np.zeros((2,2,3)))
   with self.assertRaises(ValueError):e.process(2,force=np.zeros((2,2,3)))
 def test_friction_is_reusable_parameter_not_waveform_effect(self):
  s=scene('frictionless',cells=(4,2,3),duration=1.)
  with SimulationEngine(s) as e:r=e.render()
  self.assertGreater(np.linalg.norm(r['flux']-self.r['flux']),1e-10)

if __name__=='__main__':unittest.main()
