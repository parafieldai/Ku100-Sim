"""Independent pairwise dynamics: not a perceptual silicone/hand validation."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.integrate import solve_ivp
from ku100sim.unified import SimulationEngine, ROOT


def scene(law='normal_contact', duration=.03):
    nodes=[{'id':name,'mass_kg':.005,'k2_n_m':0.,'limit_m':.01,
            'initial':{'q_m':0.,'v_m_s':.08 if name=='a' else 0.}}
           for name in ('a','b')]
    return {'schema':'shared-mechanics/1','name':'two bodies','duration_s':duration,'nodes':nodes,
            'bodies':[{'id':name,'material':'unmeasured surrogate','role':'test body','nodes':[name]} for name in ('a','b')],
            'interactions':[{'id':'pair','law':law,'a':'a','b':'b','stiffness_n_m':2000.,'gap_m':.0003 if law=='normal_contact' else 0.}],
            'evidence':{'status':'numerical_test','limits':'Reduced 1D contact, not a hand mesh or calibrated sound.'}}


def states(engine, count=1024):
    rows=[]
    while engine.frame<round(engine.rate*engine.duration):
        rows.append(engine.process(min(count,round(engine.rate*engine.duration)-engine.frame)))
    return np.concatenate(rows)


class InteractionTests(unittest.TestCase):
    def test_two_body_collision_conserves_momentum_and_energy(self):
        with SimulationEngine(scene()) as e:
            x=states(e);forces=e.interaction_readout(x)['pair']
        np.testing.assert_allclose(.005*(x[:,2]+x[:,3]),.005*.08,rtol=0,atol=2e-14)
        self.assertLess(np.max(abs(x[:,-1])),1e-12)
        np.testing.assert_allclose(x[-1,2:4],[0.,.08],atol=5e-6)
        np.testing.assert_array_equal(forces['force_on_a_n'],-forces['force_on_b_n'])
        self.assertGreater(forces['force_n'].max(),0.)
        self.assertEqual(forces['force_n'][-1],0.)

    def test_collision_against_independent_continuous_ode(self):
        s=scene()
        with SimulationEngine(s) as e:
            x=states(e);t=np.arange(1,len(x)+1)/e.rate
        def rhs(t,x):
            force=2000*max(x[0]-x[1]-.0003,0.)
            return [x[2],x[3],-force/.005,force/.005]
        ref=solve_ivp(rhs,(0,s['duration_s']),[0.,0.,.08,0.],t_eval=t,method='DOP853',rtol=1e-11,atol=1e-13,max_step=1/40000).y.T
        self.assertLess(np.max(abs(x[:,:4]-ref)/np.array([.001,.001,.08,.08])),3e-5)

    def test_link_memory_against_independent_continuous_ode(self):
        s=scene('viscoelastic_link');s['nodes'][0]['initial']={'q_m':.0004,'v_m_s':0.}
        s['interactions'][0].update(stiffness_n_m=700.,k4_n_m3=1e8,damping_n_s_m=.08,memory={'stiffness_n_m':350.,'tau_s':.007})
        with SimulationEngine(s) as e:
            x=states(e);t=np.arange(1,len(x)+1)/e.rate
        def rhs(t,x):
            z=x[0]-x[1];dv=x[2]-x[3]
            force=700*z+1e8*z**3+.08*dv+350*x[4]
            return [x[2],x[3],-force/.005,force/.005,dv-x[4]/.007]
        ref=solve_ivp(rhs,(0,s['duration_s']),[.0004,0.,0.,0.,0.],t_eval=t,method='DOP853',rtol=1e-12,atol=1e-14).y.T
        got=x[:,[0,1,2,3,6]]
        self.assertLess(np.max(abs(got-ref)/np.array([.0004,.0004,.2,.2,.0004])),5e-5)
        self.assertLess(np.max(abs(x[:,-1])),1e-12)
        self.assertGreater(x[-1,-2],0.)
        self.assertTrue(np.all(np.diff(x[:,-4])<=1e-13))

    def test_block_invariance(self):
        with SimulationEngine(scene()) as a,SimulationEngine(scene()) as b:
            np.testing.assert_array_equal(states(a,43),states(b,2048))

    def test_no_pull_detached(self):
        s=scene()
        for n in s['nodes']:n['initial']={}
        with SimulationEngine(s) as e:x=states(e)
        self.assertFalse(np.any(x))

    def test_no_algorithm_selected_by_body_material_name(self):
        a=scene();b=copy.deepcopy(a)
        for body in b['bodies']:
            body['material']='water/plastic/skin: metadata only';body['id']='renamed-'+body['id']
        with SimulationEngine(a) as x,SimulationEngine(b) as y:
            np.testing.assert_array_equal(states(x),states(y))

    def test_translation_invariance_of_internal_link(self):
        a=scene('viscoelastic_link');b=copy.deepcopy(a)
        for node in b['nodes']:node['initial']['q_m']+=.002
        with SimulationEngine(a) as x,SimulationEngine(b) as y:
            u=states(x);v=states(y)
        np.testing.assert_allclose(v[:,:2]-u[:,:2],.002,atol=1e-13)
        np.testing.assert_allclose(v[:,2:],u[:,2:],atol=1e-12)

    def test_reversing_normal_and_endpoints_preserves_contact(self):
        a=scene();b=copy.deepcopy(a);b['interactions'][0].update(a='b',b='a',normal_sign=-1)
        with SimulationEngine(a) as x,SimulationEngine(b) as y:np.testing.assert_array_equal(states(x),states(y))

    def test_contact_requires_material_pair_and_unique_ownership(self):
        for change in ('none','same','duplicate'):
            s=scene()
            if change=='none':s.pop('bodies')
            elif change=='same':s['bodies']=[dict(s['bodies'][0],nodes=['a','b'])]
            else:s['bodies'][0]['nodes'].append('b')
            with self.assertRaises(ValueError):SimulationEngine(s)

    def test_unknown_law_and_fake_wetness_rejected(self):
        for change in ('law','wetness'):
            s=scene()
            if change=='law':s['interactions'][0]['law']='water_splash'
            else:s['interactions'][0]['wetness']=1
            with self.assertRaises(ValueError):SimulationEngine(s)

    def test_invalid_parameters(self):
        for key,value in [('stiffness_n_m',-1),('stiffness_n_m',10**1000),('gap_m',float('nan')),('normal_sign',True),('normal_sign',2),('damping_n_s_m',.1),('memory',{'stiffness_n_m':0.})]:
            s=scene();s['interactions'][0][key]=value
            with self.assertRaises(ValueError):SimulationEngine(s)

    def test_no_recording_access(self):
        with SimulationEngine(scene()) as e:
            with patch('builtins.open',side_effect=AssertionError('no recording')),patch('numpy.load',side_effect=AssertionError('no array')):
                self.assertTrue(np.isfinite(e.render()['velocity']).all())

    def test_live_force_changes_both_bodies(self):
        s=scene('viscoelastic_link',.01)
        for node in s['nodes']:node['initial']={}
        with SimulationEngine(s) as e:
            x=e.process(1000,force=np.tile([.1,0.],(1000,1)))
        self.assertGreater(x[-1,0],0);self.assertGreater(x[-1,1],0)
        self.assertLess(np.max(abs(x[:,-1])),1e-12)

    def test_binaural_export_contains_full_state_layout(self):
        import tempfile
        from scripts.render_unified import render_file
        from scipy.io import wavfile
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);source=folder/'scene.json';source.write_text(json.dumps(scene('viscoelastic_link')))
            report=render_file(source,folder/'render',gain=.1,stiffness_scale=2,damping_scale=1.5)
            resolved=json.loads((folder/'render/scene.json').read_text())
            self.assertEqual(resolved['interactions'][0]['stiffness_n_m'],4000.)
            csv=(folder/'render/trace.csv').read_text().splitlines()
            self.assertEqual(len(csv[0].split(',')),len(csv[1].split(',')))
            self.assertIn('pair.memory_m',csv[0])
            rate,y=wavfile.read(folder/'render/audio.wav')
            self.assertEqual(rate,48000);self.assertEqual(y.shape[1],2)
            self.assertFalse(np.array_equal(y[:,0],y[:,1]))
            self.assertEqual(report['interaction_count'],1)

    def test_reaction_during_opposed_squeeze_and_release(self):
        s=json.loads((ROOT/'scenes/interactions/opposed-grip.json').read_text())
        with SimulationEngine(s) as e:
            r=e.render();read=e.interaction_readout(r['trace'][:,1:]);trace=r['trace']
        self.assertEqual(r['report']['body_count'],3)
        self.assertEqual(r['report']['interaction_count'],3)
        self.assertLess(r['report']['relative_balance_error'],1e-6)
        # This is a normal-contact mechanics condition, not an ASMR acceptance test.
        for key in ('thumb_to_object','index_to_object'):
            self.assertGreater(read[key]['force_n'].max(),.05)
            self.assertEqual(read[key]['force_n'][-1],0.)
        self.assertGreater(read['object_deformation']['strain_m'].max(),.0002)
        self.assertGreater(r['report']['dissipation_j'],0)

if __name__=='__main__':unittest.main()
