"""Independent equations and object-name independence for shared mechanics."""
import copy,json,math,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.integrate import solve_ivp
from ku100sim.unified import ROOT,SimulationEngine,validate_scene,preview_audio


def base(duration=.08):
 return {'schema':'shared-mechanics/1','name':'unnamed test','duration_s':duration,'nodes':[{
   'id':'a','mass_kg':.001,'k2_n_m':100.,'damping_n_s_m':.02,'limit_m':.002,
   'initial':{'q_m':.0005},'driver':{}}],
   'evidence':{'status':'numerical_test','limits':'Not a recording.'}}


def allstates(engine,block=2048):
 arrays=[];N=round(engine.duration*engine.rate)
 while engine.frame<N: arrays.append(engine.process(min(block,N-engine.frame)))
 return np.concatenate(arrays)


class UnifiedTests(unittest.TestCase):
 def test_closed_form_damped_mode(self):
  s=base();node=s['nodes'][0];node['initial']={'q_m':.0005,'v_m_s':.012}
  with SimulationEngine(s) as e:y=allstates(e);t=np.arange(1,len(y)+1)/e.rate
  m,k,d=.001,100,.02;alpha=d/(2*m);w=math.sqrt(k/m-alpha**2);A=.0005;B=(.012+alpha*A)/w
  q=np.exp(-alpha*t)*(A*np.cos(w*t)+B*np.sin(w*t))
  v=np.exp(-alpha*t)*((B*w-alpha*A)*np.cos(w*t)+(-A*w-alpha*B)*np.sin(w*t))
  np.testing.assert_allclose(y[:,0],q,atol=2e-14,rtol=2e-9);np.testing.assert_allclose(y[:,1],v,atol=2e-12,rtol=2e-9)
  self.assertLess(abs(y[:,-1]).max(),1e-14)
 def test_metadata_never_selects_sound(self):
  s=base();t=copy.deepcopy(s);t['name']='silicone-wood-plastic-tuning-fork';t['description']='anything'
  with SimulationEngine(s) as a, SimulationEngine(t) as b:
   np.testing.assert_array_equal(allstates(a),allstates(b))
 def test_block_invariance(self):
  s=base();s['nodes'][0]['k4_n_m3']=1e8
  with SimulationEngine(s) as a,SimulationEngine(s) as b:
   np.testing.assert_array_equal(allstates(a,73),allstates(b,2048))
 def test_zero_is_zero(self):
  s=base();s['nodes'][0]['initial']={}
  with SimulationEngine(s) as e:y=allstates(e)
  self.assertFalse(np.any(y))
 def test_nonlinear_free_energy(self):
  s=base();s['nodes'][0].update(k4_n_m3=2e9,damping_n_s_m=0)
  with SimulationEngine(s) as e:y=allstates(e)
  self.assertLess(np.ptp(y[:,-4])/y[0,-4],1e-8)
 def test_relaxation_against_independent_ode(self):
  s=base();s['nodes'][0].update(k4_n_m3=1e8,memory={'stiffness_n_m':250,'tau_s':.006})
  with SimulationEngine(s) as e:y=allstates(e);t=np.arange(1,len(y)+1)/e.rate
  def rhs(t,z):q,v,r=z;return [v,(-100*q-1e8*q**3-.02*v-250*r)/.001,v-r/.006]
  ref=solve_ivp(rhs,(0,s['duration_s']),[.0005,0,0],t_eval=t,method='DOP853',rtol=1e-11,atol=1e-13).y.T
  scales=np.array([.0005,.0005*math.sqrt(350/.001),.0005])
  self.assertLess(np.max(abs(y[:,:3]-ref)/scales),2e-5)
  self.assertGreater(y[-1,-2],0);self.assertLess(abs(y[:,-1]).max(),1e-12)
 def test_shared_coupling_reciprocity_and_energy(self):
  s=base();b=copy.deepcopy(s['nodes'][0]);b['id']='b';b['initial']={};s['nodes'].append(b)
  s['couplings']=[{'a':'a','b':'b','stiffness_n_m':80}]
  with SimulationEngine(s) as e:y=allstates(e)
  t=copy.deepcopy(s);t['nodes'][0]['initial']={};t['nodes'][1]['initial']={'q_m':.0005}
  with SimulationEngine(t) as e:z=allstates(e)
  np.testing.assert_allclose(y[:,0],z[:,1],atol=2e-15);self.assertGreater(abs(y[:,1]).max(),1e-5)
  self.assertLess(abs(y[:,-1]).max(),1e-12)
 def test_material_parameters_not_equalization(self):
  s=base(.1);s['nodes'][0]['damping_n_s_m']=0;t=copy.deepcopy(s);t['nodes'][0]['k2_n_m']*=4
  with SimulationEngine(s) as a,SimulationEngine(t) as b:
   x=allstates(a)[:,0];y=allstates(b)[:,0]
  count=lambda z:np.count_nonzero(z[1:]*z[:-1]<0)
  self.assertLessEqual(abs(count(y)-2*count(x)),1)
 def test_unilateral_no_pull_when_detached(self):
  s=base();s['nodes'][0]['initial']={};s['nodes'][0]['driver']={'stiffness_n_m':1000,'unilateral':True,'displacement':[[0,-.001],[.08,-.001]]}
  with SimulationEngine(s) as e:y=allstates(e)
  self.assertFalse(np.any(y))
 def test_contact_crossing_work_balance(self):
  s=base();s['nodes'][0]['initial']={};s['nodes'][0]['driver']={'stiffness_n_m':300,'unilateral':True,'displacement':[[0,-.0002],[.02,.0004],[.04,.0004],[.06,-.0002],[.08,-.0002]]}
  with SimulationEngine(s) as e:y=allstates(e)
  self.assertGreater(y[:,-3].max(),0);self.assertLess(abs(y[:,-1]).max(),2e-12)
 def test_live_force_same_as_table(self):
  s=base();s['nodes'][0]['initial']={}
  with SimulationEngine(s) as a,SimulationEngine(s) as b:
   u,f=a.control_at(np.arange(1,101)/a.rate)
   np.testing.assert_array_equal(a.process(100),b.process(100,displacement=u,force=f))
   new=b.process(100,force=np.ones((100,1))*.02)
  self.assertGreater(abs(new[:,0]).max(),0)
 def test_invalid_live_input_not_advancing(self):
  with SimulationEngine(base()) as e:
   with self.assertRaises(ValueError):e.process(3,force=np.full((3,1),np.nan))
   self.assertEqual(e.frame,0)
 def test_unknown_parameters_rejected(self):
  s=base();s['nodes'][0]['wetness']=.8
  with self.assertRaises(ValueError):SimulationEngine(s)
 def test_invalid_physics_rejected(self):
  for key,value in [('mass_kg',-1),('k4_n_m3',-1),('damping_n_s_m',-1),('k2_n_m',-10)]:
   s=base();s['nodes'][0][key]=value
   with self.assertRaises(ValueError):SimulationEngine(s)
 def test_stiffness_resolution_rejected(self):
  s=base();s['nodes'][0]['k2_n_m']=1e10
  with self.assertRaises(ValueError):SimulationEngine(s)
 def test_domain_exceedance_poisoned(self):
  s=base();s['nodes'][0].update(limit_m=.00051,initial={'q_m':.0005,'v_m_s':5})
  with SimulationEngine(s) as e:
   with self.assertRaises(RuntimeError):e.process(100)
   with self.assertRaises(RuntimeError):e.process(1)
 def test_preview_antialias_and_output_domain(self):
  fs=192000;t=np.arange(fs)/fs
  y=preview_audio(.01*np.sin(2*np.pi*30000*t),fs,1)
  self.assertLess(abs(y[2000:-2000]).max(),1e-6)
  self.assertFalse(np.array_equal(y[:,0],y[:,1]))
  self.assertEqual(y.shape,(48000+223,2))
 def test_no_file_read_during_render(self):
  with SimulationEngine(base()) as e:
   with patch('builtins.open',side_effect=AssertionError('recording read')),patch('numpy.load',side_effect=AssertionError('array read')):
    self.assertTrue(np.isfinite(e.render()['velocity']).all())
 def test_all_scene_definitions_compile(self):
  for path in (ROOT/'scenes/unified').glob('*.json'):
   with SimulationEngine(json.loads(path.read_text())) as e:
    self.assertTrue(np.isfinite(e.process(64)).all())
 def test_arbitrary_composed_graph_no_new_class(self):
  s=base();s['nodes'].append({'id':'nonlinear','mass_kg':.002,'k2_n_m':-30,'k4_n_m3':1e8,'limit_m':.002,
    'memory':{'stiffness_n_m':15,'tau_s':.003},'initial':{'q_m':.0005}})
  s['couplings']=[{'a':'a','b':'nonlinear','stiffness_n_m':20}]
  with SimulationEngine(s) as e:r=e.render()
  self.assertEqual(r['report']['integrator'],'discrete_gradient');self.assertLess(r['report']['relative_balance_error'],1e-6)

if __name__=='__main__':unittest.main()
