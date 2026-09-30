import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from ku100sim import texture_source as ts
from ku100sim.burst_source import load_model
from scripts.build_texture_iteration import phase_control,finish
ROOT=Path(__file__).resolve().parents[1]

class TextureSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=ts.load(ROOT/'models/texture-right-reference.ctm.xz')
        cls.old=load_model(ROOT/'models/burst-right.json')
    def test_schema_refuses_physical_claim_or_nonfinite(self):
        for field in ('physical_model','runtime_reference_audio','phase_or_timeline_stored'):
            m=copy.deepcopy(self.model);m[field]=True
            with self.assertRaises(ValueError):ts.validate(m)
        m=copy.deepcopy(self.model);m['statistics'][0]['mean'][0][0]=float('nan')
        with self.assertRaises(ValueError):ts.validate(m)
    def test_bad_requests_fail_before_render(self):
        for args in ({'seconds':0},{'seconds':float('nan')},{'seconds':10**400},{'seed':True},{'iterations':-1},{'iterations':1.5},{'phase_only':1}):
            with self.assertRaises(ValueError):ts.synthesize(self.model,**args)
    def test_new_seed_and_replay(self):
        a,ma=ts.synthesize(self.model,seconds=1,seed=3,iterations=3)
        b,mb=ts.synthesize(self.model,seconds=1,seed=3,iterations=3)
        c,_=ts.synthesize(self.model,seconds=1,seed=4,iterations=3)
        np.testing.assert_array_equal(a,b);self.assertGreater(np.linalg.norm(a-c),.01)
        self.assertEqual(len(a),48000);self.assertTrue(np.isfinite(a).all());self.assertLess(abs(a).max(),1)
        self.assertEqual(ma['reference_reads_at_render'],0);self.assertFalse(ma['physical_model'])
        self.assertLessEqual(ma['best_objective'],ma['history'][0]['loss'])
    def test_control_really_preserves_fourier_magnitude(self):
        x=np.random.default_rng(4).normal(size=5001);y,err=phase_control(x,8)
        self.assertLess(err,1e-12);np.testing.assert_allclose(abs(np.fft.rfft(x)),abs(np.fft.rfft(y)),atol=1e-10)
        self.assertGreater(np.linalg.norm(x-y),10)
    def test_frozen_stereo_is_linear_and_keeps_full_tail(self):
        x=np.zeros(48000);x[100]=.05
        a,ra=ts.frozen_stereo_transfer(self.old,x);b,rb=ts.frozen_stereo_transfer(self.old,x*2)
        np.testing.assert_allclose(b,2*a,atol=1e-14);self.assertEqual(len(a),49023)
        self.assertEqual(ra['coefficients_sha256'],rb['coefficients_sha256']);self.assertFalse(ra['new_spatial_fit'])
        self.assertEqual(np.argmax(abs(a[:,1])),100)
    def test_level_metadata_is_serializable_and_shared(self):
        x=np.random.default_rng(9).normal(size=48000)*.1
        y,route,gain=finish(x,self.old)
        json.dumps({'route':route,'level':gain},allow_nan=False)
        self.assertLessEqual(abs(y).max(),.600001);self.assertFalse(gain['output_eq_applied'])
    def test_reference_fit_is_not_mislabeled_as_holdout(self):
        p=self.model['provenance'];self.assertEqual(p['fit_scope'],'reference_excerpt')
        self.assertEqual(p['ranges_s'],[[57,63]]);self.assertIsNone(p['comparison_excluded_s'])
        self.assertFalse(p['target_sample_sequence_exported'])
    def test_load_rejects_duplicate_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(ValueError):ts.load(p)
    def test_compressed_expansion_is_bounded(self):
        import lzma
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.xz';p.write_bytes(lzma.compress(b' '*500001))
            with self.assertRaises(ValueError):ts.load(p)
if __name__=='__main__':unittest.main()
