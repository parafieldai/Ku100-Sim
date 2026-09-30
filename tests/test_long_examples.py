import unittest
import numpy as np
from scripts.build_long_examples import join_fresh

class LongExamplesTests(unittest.TestCase):
 def test_length_and_no_modification_outside_overlap(self):
  a=np.arange(12,dtype=float);b=np.arange(12,dtype=float)+50;c=b+50
  y=join_fresh([a,b,c],3)
  self.assertEqual(len(y),30);np.testing.assert_array_equal(y[:9],a[:9]);np.testing.assert_array_equal(y[-9:],c[3:])
 def test_overlap_endpoints(self):
  a=np.ones(12);b=np.ones(12)*2;y=join_fresh([a,b],3)
  self.assertAlmostEqual(y[9],1.);self.assertAlmostEqual(y[11],2.)
 def test_reject_invalid(self):
  for a,n in [([np.zeros(4)],1),([np.zeros(4),np.zeros(4)],4),([np.full(4,np.nan),np.zeros(4)],1)]:
   with self.assertRaises(ValueError):join_fresh(a,n)

class LongPublicationTests(unittest.TestCase):
 def _fixture(self,root):
  import json
  from scripts.long_publication import APP,IDS
  for name in APP:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test')
  folder=root/'long/generated';folder.mkdir()
  rows=[]
  for slug in IDS:
   (folder/(slug+'.wav')).write_bytes(b'unit-fixture')
   rows.append({'id':slug,'file':slug+'.wav','frames':(30 if slug=='long-right' else 12)*48000+1023,'sample_rate':48000,'sha256':'unit-fixture'})
  m={'schema':'long-texture-examples/1','physical_model':False,'reference_audio_public':False,'pressure_control_implemented':False,'source_recording_reads':0,'source_recording_read_attempts':0,'samples':rows}
  (folder/'manifest.json').write_text(json.dumps(m));return m
 def test_exact_allowlist(self):
  import tempfile,json
  from pathlib import Path
  from scripts.long_publication import collect,FILES
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self._fixture(root)
   files=collect(root,lambda p,n:p.read_bytes(),lambda b,label:json.loads(b),lambda *a:None)
   self.assertEqual(set(files),set(FILES))
 def test_private_file_rejected(self):
  import tempfile,json
  from pathlib import Path
  from scripts.long_publication import collect
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self._fixture(root);(root/'long/generated/reference.wav').write_bytes(b'not-allowed')
   with self.assertRaises(ValueError):collect(root,lambda p,n:p.read_bytes(),lambda b,label:json.loads(b),lambda *a:None)
 def test_physical_claim_rejected(self):
  import tempfile,json
  from pathlib import Path
  from scripts.long_publication import collect
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m=self._fixture(root);m['physical_model']=True;(root/'long/generated/manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):collect(root,lambda p,n:p.read_bytes(),lambda b,label:json.loads(b),lambda *a:None)

if __name__=='__main__':unittest.main()
