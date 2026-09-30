import hashlib,json,shutil,struct,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts.build_object_examples import IDS,wav16
from scripts.object_publication import APP,FILES,collect,validate_wav
from scripts.build_site import _read_file,_json

class ObjectPublicationTests(unittest.TestCase):
    def fixture(self,root):
        for name in APP:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test')
        folder=root/'objects/generated';folder.mkdir();rows=[]
        for slug in IDS:
            kind=slug.rsplit('-',1)[-1];frames=48000 if kind=='prior' else 192000
            x=np.zeros(frames);x[10:20]=.1;raw=wav16(x);(folder/(slug+'.wav')).write_bytes(raw)
            rows.append({'id':slug,'kind':kind,'file':slug+'.wav','frames':frames,'rate':48000,'channels':2,'pcm_bits':16,'sha256':hashlib.sha256(raw).hexdigest()})
        m={'schema':'object-sfx-preview/1','reference_audio_public':False,'old_ear_recordings_used':False,'render_from_recording':False,'physical_calibration':False,'pressure_control':False,'raw_reference_audio_embedded':False,'headphone_spatialization':'dual mono, not KU100 transfer','listener_judgment':'not performed','samples':rows}
        (folder/'manifest.json').write_text(json.dumps(m));return m
    def test_complete_canonical_pcm_population(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);self.assertEqual(set(collect(root,_read_file,_json)),set(FILES))
    def test_unlisted_reference_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);extra=root/'objects/generated/reference.wav';extra.write_bytes(b'reference')
            with self.assertRaises(ValueError):collect(root,_read_file,_json)
            extra.unlink();target=root/'objects/app.js';target.unlink();target.symlink_to(root/'objects/index.html')
            with self.assertRaises(ValueError):collect(root,_read_file,_json)
    def test_claims_and_embedded_recordings_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.fixture(root);file=root/'objects/generated/manifest.json'
            for field in ('physical_calibration','reference_audio_public','old_ear_recordings_used','render_from_recording'):
                m[field]=True;file.write_text(json.dumps(m))
                with self.assertRaises(ValueError):collect(root,_read_file,_json)
                m[field]=False
            m['nested']={'reference_waveform':[0,1]};file.write_text(json.dumps(m))
            with self.assertRaises(ValueError):collect(root,_read_file,_json)
    def test_pcm_corruption_even_with_new_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.fixture(root);row=m['samples'][0];original=(root/'objects/generated'/row['file']).read_bytes()
            for raw in [original+b'extra',original[:20]+struct.pack('<H',3)+original[22:],original[:24]+struct.pack('<I',44100)+original[28:]]:
                altered=dict(row,sha256=hashlib.sha256(raw).hexdigest())
                with self.assertRaises(ValueError):validate_wav(raw,altered)
            with self.assertRaises(ValueError):validate_wav(original,dict(row,sha256='0'*64))
    def test_silence_and_stereo_remix_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.fixture(root);row=m['samples'][0];raw=wav16(np.zeros(row['frames']))
            with self.assertRaises(ValueError):validate_wav(raw,dict(row,sha256=hashlib.sha256(raw).hexdigest()))
            raw=bytearray((root/'objects/generated'/row['file']).read_bytes());raw[46:48]=struct.pack('<h',100);raw=bytes(raw)
            with self.assertRaises(ValueError):validate_wav(raw,dict(row,sha256=hashlib.sha256(raw).hexdigest()))
    def test_filename_traversal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.fixture(root);m['samples'][0]['file']='../../reference.wav';(root/'objects/generated/manifest.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):collect(root,_read_file,_json)
if __name__=='__main__':unittest.main()
