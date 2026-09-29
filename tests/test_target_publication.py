"""Keep reference waveforms and unearned success flags outside public builds."""
import base64,json,sys
from pathlib import Path
import tempfile,unittest
from copy import deepcopy
from scripts import build_site
from test_site import fixture_bundle
class TargetPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.web=self.root/'web';(self.web/'examples').mkdir(parents=True)
        for name in build_site.APP_FILES:(self.web/name).write_text('test asset')
        b=fixture_bundle();(self.web/'examples/fixture.ku100.json').write_text(json.dumps(b))
        (self.web/'examples/index.json').write_text(json.dumps({'version':1,'examples':[{'id':'fixture','title':'Test','description':'Synthetic fixture','path':'fixture.ku100.json'}]}))
        self.study={'version':'ku100-target-study/1','reference_audio_included':False,'physical_target_accepted':False,'cases':[{'id':f'case-{i}','kind':'generated-source-hypothesis','metrics':{'sample_rate_hz':48000,'duration_s':16/48000},'audio':b['audio']} for i in range(4)]}
        self.summary={'version':'ku100-reference-summary/1','reference_audio_included':False,'references':[]}
    def build(self):
        (self.web/'target-study.json').write_text(json.dumps(self.study));(self.web/'target-reference-summary.json').write_text(json.dumps(self.summary))
        return build_site.build_site(self.web,self.root/'dist')
    def test_generated_study_and_small_derived_reference_summary_publish(self):
        self.assertIn('target-study.json',self.build()['files'])
    def test_reference_audio_and_unearned_acceptance_flags_reject(self):
        for key in ['reference_audio_included','physical_target_accepted']:
            with self.subTest(key=key):
                self.study[key]=True
                with self.assertRaises(ValueError):self.build()
                self.study[key]=False
    def test_reference_samples_reject_even_when_flag_says_false(self):
        for key in ['audio','samples','base64','waveform']:
            with self.subTest(key=key):
                self.summary['references']=[{key:'AAAA'}]
                with self.assertRaises(ValueError):self.build()
    def test_generated_waveform_corruption_cannot_publish(self):
        self.study['cases'][0]['audio']=deepcopy(self.study['cases'][0]['audio']);self.study['cases'][0]['audio']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SHA-256'):self.build()
    def test_reference_kind_cannot_be_mislabeled_as_generation(self):
        self.study['cases'][0]['kind']='reference'
        with self.assertRaises(ValueError):self.build()
    def test_private_packager_refuses_public_destination(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from package_target import package,ROOT
        with self.assertRaisesRegex(ValueError,'publication'):
            package(ROOT/'dist/private.html',references=self.root)
if __name__=='__main__':unittest.main()
