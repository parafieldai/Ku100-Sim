"""The new source page must not weaken the existing private-reference boundary."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.texture_publication import collect, APP, IDS
from scripts.build_site import _read_file, _json

class SourcePublicationTests(unittest.TestCase):
    def fixture(self, root):
        for p in APP:
            q=root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('test')
        gen=root/'source/generated';gen.mkdir()
        rows=[]
        for id in IDS:
            (gen/(id+'.wav')).write_bytes(b'test')
            rows.append({'id':id,'file':id+'.wav','kind':'revision','sample_rate':48000,'frames':48000,'sha256':'0'*64})
        m={'schema':'source-iteration/1','reference_audio_public':False,'physical_model':False,'target_accepted':False,'samples':rows,'reference_descriptors':[{} for _ in range(4)]}
        (gen/'iteration.json').write_text(json.dumps(m));return gen,m
    def run_collect(self, root):
        return collect(root,_read_file,_json,lambda *args:None)
    def test_complete_explicit_population(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r);self.assertEqual(len(self.run_collect(r)),11)
    def test_private_reference_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);gen,m=self.fixture(r);m['reference_descriptors'][0]['waveform']=[0.1]
            (gen/'iteration.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):self.run_collect(r)
    def test_unlisted_audio_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);gen,_=self.fixture(r);(gen/'original.wav').write_bytes(b'private')
            with self.assertRaises(ValueError):self.run_collect(r)
    def test_linked_generated_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);gen,_=self.fixture(r);dest=r/'elsewhere';gen.rename(dest);gen.symlink_to(dest,target_is_directory=True)
            with self.assertRaises(ValueError):self.run_collect(r)
    def test_acceptance_or_privacy_claim_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);gen,m=self.fixture(r);m['target_accepted']=True
            (gen/'iteration.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):self.run_collect(r)
