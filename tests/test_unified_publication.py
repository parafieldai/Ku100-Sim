import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ku100sim.unified import validate_scene,SimulationEngine
from tests.test_unified import base
from scripts.package_unified_site import collect

class UnifiedPublicationTests(unittest.TestCase):
 def test_new_schema_rejects_waveform_payload(self):
  s=base();s['waveform']=[0,1]
  with self.assertRaises(ValueError):validate_scene(s)
 def test_material_status_cannot_claim_calibration(self):
  s=base();s['evidence']['status']='measured'
  with self.assertRaises(ValueError):validate_scene(s)
 def test_duplicate_node_rejected(self):
  s=base();s['nodes'].append(copy.deepcopy(s['nodes'][0]))
  with self.assertRaises(ValueError):validate_scene(s)
 def test_bad_coupling_rejected(self):
  s=base();s['couplings']=[{'a':'a','b':'missing','stiffness_n_m':1}]
  with self.assertRaises(ValueError):validate_scene(s)
 def test_unresolved_surface_rejected(self):
  s=base();s['nodes'][0]['driver']={'travel':[[0,0],[.08,1]],'roughness':[{'amplitude_m':1e-6,'wavelength_m':1e-6}]}
  with self.assertRaises(ValueError):validate_scene(s)
 def test_unknown_asset_not_published(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'unified';p.mkdir();(p/'reference.wav').write_bytes(b'private')
   with self.assertRaises(ValueError):collect(Path(d))
 def test_symlink_not_published(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'unified';p.mkdir();(p/'reference.wav').symlink_to('/tmp/missing')
   with self.assertRaises(ValueError):collect(Path(d))
 def test_overlarge_number_rejected(self):
  s=base();s['nodes'][0]['mass_kg']=10**1000
  with self.assertRaises(ValueError):validate_scene(s)

if __name__=='__main__':unittest.main()
