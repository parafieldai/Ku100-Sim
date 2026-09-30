import copy,json,hashlib,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ku100sim.burst_source import load_model,synthesize,filter_bank,wav_bytes,validate_model,event_candidates
from ku100sim.audio import read_wav
from ku100sim.target_metrics import stats,compare_stats
from scripts.render_burst_source import render

class BurstSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=load_model(ROOT/'models/burst-right.json')
        cls.x,cls.meta=synthesize(cls.model,seconds=2.,seed=1)
    def test_fresh_seed_determinism_and_explicit_nonphysical_identity(self):
        a,_=synthesize(self.model,seconds=2.,seed=1);b,_=synthesize(self.model,seconds=2.,seed=2)
        np.testing.assert_array_equal(a,self.x);self.assertFalse(np.array_equal(a,b))
        self.assertFalse(self.meta['physical_model']);self.assertFalse(self.meta['mechanism_identified'])
        self.assertEqual(self.meta['runtime_reference_audio_reads'],0)
    def test_synthesis_performs_no_file_or_reference_reads(self):
        with patch('builtins.open',side_effect=AssertionError('unexpected runtime file')),patch.object(Path,'read_bytes',side_effect=AssertionError('unexpected runtime file')):
            a,meta=synthesize(self.model,seconds=1.,seed=4)
        self.assertTrue(np.isfinite(a).all());self.assertTrue(meta['events'])
    def test_gate_zero_and_tail_keep_exact_silence(self):
        a,m=synthesize(self.model,seconds=1.,gate_end=0)
        self.assertFalse(np.any(a));self.assertFalse(m['events'])
        b,m=synthesize(self.model,seconds=1.,gate_end=.6)
        self.assertFalse(np.any(b[round(.65*48000):]))
    def test_stereo_not_duplicated_or_normalized_independently(self):
        a=self.x;self.assertGreater(np.linalg.norm(a[:,1])/np.linalg.norm(a[:,0]),20)
        self.assertFalse(np.array_equal(a[:,0],a[:,1]))
        model=copy.deepcopy(self.model);model['near_channel']=0;model['log_magnitude']=np.array(model['log_magnitude'])[:,::-1].tolist()
        b,_=synthesize(model,seconds=2.,seed=1);np.testing.assert_array_equal(a,b[:,::-1])
    def test_control_and_model_rejection(self):
        for kwargs in [{'seconds':float('nan')},{'seconds':True},{'seconds':31},{'seed':True},{'seed':-1},{'rate_scale':0},{'gate_end':-1},{'continuous_ablation':'yes'}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):synthesize(self.model,**kwargs)
        for key,value in [('physical_model',True),('near_channel',True),('rms_median',10**400),('log_magnitude',[[0]])]:
            m=copy.deepcopy(self.model);m[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_model(m)
    def test_wav_roundtrip_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.wav';p.write_bytes(wav_bytes(self.x));rate,y=read_wav(p)
            self.assertEqual(rate,48000);np.testing.assert_array_equal(y,self.x.astype(np.float32).astype(float))
            out=Path(d)/'render';meta=render(ROOT/'models/burst-right.json',out,seconds=1.,seed=5)
            self.assertEqual(meta['audio_sha256'],hashlib.sha256((out/'audio.wav').read_bytes()).hexdigest())
            with self.assertRaises(ValueError):render(ROOT/'models/burst-right.json',out)
        for x,rate in [(np.array([[1e50,0.]]),48000),(self.x,0),(self.x,True),(np.zeros((0,2)),48000)]:
            with self.assertRaises(ValueError):wav_bytes(x,rate)
    def test_negative_control_is_a_distinct_waveform_not_a_second_reference(self):
        b,m=synthesize(self.model,seconds=2.,seed=1,continuous_ablation=True)
        self.assertFalse(np.array_equal(self.x,b));self.assertTrue(m['continuous_ablation']);self.assertFalse(m['events'])
    def test_fitting_windows_exclude_the_selected_references(self):
        refs=json.loads((ROOT/'validation/target/reference-targets.json').read_text())['references']
        for side in ['right','left']:
            m=load_model(ROOT/f'models/burst-{side}.json')
            self.assertFalse(m['fitting']['runtime_samples_or_event_timeline'])
            for ref in refs:
                if ref['sha256']==m['fitting']['file_sha256']:
                    lo,hi=ref['crop_s']
                    self.assertTrue(all(b<=lo or a>=hi for a,b in m['fitting']['ranges_s']))
    def test_quiet_ear_error_is_exposed_separately_from_loud_ear(self):
        rng=np.random.default_rng(3);x=rng.normal(size=(48000,2));x[:,0]*=.001
        a=stats(48000,x);b=x.copy();b[:,0]*=10;c=compare_stats(a,stats(48000,b))
        self.assertAlmostEqual(c['ild_error_db'],20.,places=8);self.assertFalse(c['mechanical_controls_validated'])
        silent=stats(48000,np.zeros((48000,2)));self.assertIsNone(silent['ild_left_minus_right_db'])
