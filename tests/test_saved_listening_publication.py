import base64,hashlib,json,shutil,tempfile,unittest,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_site import _target_files,TARGET_APP,TARGET_NAMES
from ku100sim.burst_source import wav_bytes

class TargetPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'web';(self.root/'target/generated').mkdir(parents=True)
        for name in TARGET_APP:(self.root/name).write_text('test fixture')
        raw=wav_bytes(np.zeros((48000,2)));self.study={'schema':'target-listening-study/1','reference_audio_public':False,'physical_target_implemented':False,'status':'target_not_accepted','candidates':[]}
        for name in TARGET_NAMES:
            (self.root/'target/generated'/f'{name}.wav').write_bytes(raw)
            self.study['candidates'].append({'id':name,'file':name+'.wav','sha256':hashlib.sha256(raw).hexdigest(),'metrics':{'duration_s':1.}})
        self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):(self.root/'target/generated/study.json').write_text(json.dumps(self.study))
    def test_only_known_generated_audio_is_included(self):self.assertEqual(len(_target_files(self.root)),11)
    def test_unlisted_private_reference_is_refused(self):
        (self.root/'target/generated/private-reference.wav').write_bytes(b'private')
        with self.assertRaises(ValueError):_target_files(self.root)
    def test_reference_embed_or_changed_scope_is_refused(self):
        for update in [{'base64':'eA=='},{'reference_audio_public':True},{'physical_target_implemented':True},{'status':'accepted'}]:
            old=self.study.copy();self.study.update(update);self.save()
            with self.assertRaises(ValueError):_target_files(self.root)
            self.study=old
    def test_changed_audio_and_traversal_and_invalid_duration_are_refused(self):
        for change in [{'file':'../private.wav'},{'sha256':'a'*64},{'metrics':{'duration_s':10**400}}]:
            old=self.study['candidates'][0].copy();self.study['candidates'][0].update(change);self.save()
            with self.assertRaises(ValueError):_target_files(self.root)
            self.study['candidates'][0]=old
    def test_symlinked_generated_asset_is_refused(self):
        p=self.root/'target/generated/burst-right-a.wav';p.unlink();p.symlink_to(self.root/'target/generated/burst-right-b.wav')
        with self.assertRaises(ValueError):_target_files(self.root)
