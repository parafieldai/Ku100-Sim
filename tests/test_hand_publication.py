import tempfile,unittest
from pathlib import Path
from scripts.package_hand_site import collect,expected
class HandPublicationTests(unittest.TestCase):
 def test_exact_public_names_have_no_recording_or_data_archive(self):
  names=expected();self.assertEqual(len(names),45)
  self.assertFalse(any('reference' in n or n.endswith(('.zip','.npz','.csv')) for n in names))
 def test_unlisted_file_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'hand').mkdir();(root/'fork-radiation').mkdir();(root/'hand/private-reference.wav').write_bytes(b'no')
   with self.assertRaisesRegex(ValueError,'Unlisted'):collect(root)
 def test_linked_asset_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'hand').mkdir();(root/'fork-radiation').mkdir();(root/'hand/index.html').symlink_to(root/'fork-radiation')
   with self.assertRaisesRegex(ValueError,'Linked'):collect(root)
 def test_missing_assets_fail(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'hand').mkdir();(root/'fork-radiation').mkdir()
   with self.assertRaisesRegex(ValueError,'Missing'):collect(root)
if __name__=='__main__':unittest.main()
