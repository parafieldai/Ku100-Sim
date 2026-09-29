"""Documented input contracts: malformed WAVs and finite publication values.

These are software regressions, not subagent reviews or perceptual checks.
"""
from pathlib import Path
import json
import struct
import tempfile
import unittest
import numpy as np
from ku100sim.audio import read_wav
from scripts.build_site import _number, _validate_bundle

class DocumentInputContracts(unittest.TestCase):
    def wave(self, encoding, bits, align=None, body=b''):
        align = 2*(bits//8) if align is None else align
        fmt = struct.pack('<HHIIHH', encoding, 2, 48000, 48000*align, align, bits)
        payload = b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(body))+body
        if len(body)%2: payload += b'\0'
        return b'RIFF'+struct.pack('<I',len(payload)+4)+b'WAVE'+payload

    def read(self, content):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'fixture.wav'; path.write_bytes(content)
            return read_wav(path)

    def test_zero_and_unsupported_depths_reject_without_arithmetic_error(self):
        for encoding,bits in [(1,0),(1,1),(1,8),(1,12),(1,64),(3,0),(3,16),(99,32)]:
            with self.subTest(encoding=encoding,bits=bits):
                with self.assertRaisesRegex(ValueError,'Unsupported WAVE'):
                    self.read(self.wave(encoding,bits))

    def test_zero_alignment_and_partial_frame_are_rejected(self):
        for content in [self.wave(1,16,align=0),self.wave(3,32,body=b'\0')]:
            with self.assertRaisesRegex(ValueError,'frame layout'):
                self.read(content)

    def test_supported_pcm_and_float_formats_keep_channel_order(self):
        fixtures=[(1,16,struct.pack('<hh',8192,-16384)),
                  (1,24,bytes([0,0,32,0,0,192])),
                  (1,32,struct.pack('<ii',2**29,-2**30)),
                  (3,32,struct.pack('<ff',.25,-.5)),
                  (3,64,struct.pack('<dd',.25,-.5))]
        for encoding,bits,data in fixtures:
            rate,values=self.read(self.wave(encoding,bits,body=data))
            self.assertEqual(rate,48000)
            np.testing.assert_array_equal(values,[[.25,-.5]])

    def test_exported_scene_rate_matches_native_decimator_limits(self):
        from ku100sim.scene import canonical_scene
        raw={"version":"ku100-scene/1", "physics":{}}
        defaults={"sample_rate":192000, "trace_stride":192}
        for rate in [48000,96000,192000,384000,768000]:
            raw["physics"]={"sample_rate":rate}
            self.assertEqual(canonical_scene(raw,defaults)["physics"]["sample_rate"],rate)
        for rate in [1536000,800000,8000,96000.5]:
            raw["physics"]={"sample_rate":rate}
            with self.assertRaises(ValueError): canonical_scene(raw,defaults)

    def test_huge_json_integer_is_rejected_by_numeric_predicate(self):
        for value in [10**400,-10**400,float('nan'),float('inf'),True,'1']:
            self.assertFalse(_number(value))
        for value in [0,3,1.25]: self.assertTrue(_number(value))

    def test_huge_bundle_duration_uses_value_error_contract(self):
        from test_site import fixture_bundle
        bundle=fixture_bundle();bundle['duration_s']=10**400
        with self.assertRaisesRegex(ValueError,'duration'):
            _validate_bundle(json.dumps(bundle).encode(),'oversized-integer')

if __name__=='__main__': unittest.main()
