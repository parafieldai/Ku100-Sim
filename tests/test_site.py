"""Publication-boundary regression tests, independent of native rendering."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_site


def fixture_bundle():
    samples = struct.pack("<" + "f" * 32, *([0.125, -0.0625] * 16))
    fmt = struct.pack("<HHIIHH", 3, 2, 48000, 384000, 8, 32)
    payload = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(samples)) + samples
    wav = b"RIFF" + struct.pack("<I", len(payload) + 4) + b"WAVE" + payload
    return {
        "version": "ku100-render/1",
        "scene": {"version": "ku100-scene/1", "name": "Synthetic packaging fixture", "preset": "stroke",
                  "side": "left", "duration_s": 0.02, "physics": {"load_n": 0.6}, "receiver": {"mode": "contact"}},
        "audio": {"mime": "audio/wav", "base64": base64.b64encode(wav).decode("ascii"),
                  "sha256": hashlib.sha256(wav).hexdigest(), "channels": 2},
        "sample_rate_hz": 48000, "duration_s": 16 / 48000,
        "trace": {"columns": ["time_s", "normal_force_n"], "rows": [[0, 0], [8 / 48000, 1]]},
        "metrics": {"peak": 0.125}, "provenance": {"renderer": "synthetic-test-fixture"},
        "geometry": {"units": "m", "axes": {"x": "forward", "y": "left", "z": "up"},
                     "head": {"radii_m": [0.09, 0.075, 0.11], "center_m": [0, 0, 0]},
                     "ears": [{"side": "left", "center_m": [0, 0.0875, 0]}, {"side": "right", "center_m": [0, -0.0875, 0]}],
                     "contact": {"side": "left", "patch_radius_m": 0.004}},
    }


class SitePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.web = self.root / "web"
        self.examples = self.web / "examples"
        self.examples.mkdir(parents=True)
        self.output = self.root / "dist"
        self.bundle = fixture_bundle()
        self.manifest = {"version": 1, "examples": [{"id": "fixture", "title": "Synthetic fixture",
                          "description": "This audio is generated for a packaging test.", "path": "fixture.ku100.json"}]}
        for name in build_site.APP_FILES:
            (self.web / name).write_text(f"Test application file: {name}\n")
        self.save()

    def save(self):
        (self.examples / "index.json").write_text(json.dumps(self.manifest))
        (self.examples / "fixture.ku100.json").write_text(json.dumps(self.bundle))

    def build(self):
        return build_site.build_site(self.web, self.output)

    @staticmethod
    def snapshot(directory):
        return {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob("*") if path.is_file()}

    def test_only_application_and_listed_exports_are_published(self):
        (self.web / "private-recording.wav").write_bytes(b"private sibling never published")
        (self.web / "tests").mkdir()
        (self.web / "tests" / "test.js").write_text("development-only test")
        before = self.snapshot(self.web)
        result = self.build()
        expected = set(build_site.APP_FILES) | {"examples/index.json", "examples/fixture.ku100.json"}
        self.assertEqual(set(result["files"]), expected)
        self.assertEqual(set(self.snapshot(self.output)), expected)
        self.assertEqual(self.snapshot(self.web), before)
        self.assertEqual(result["examples"], 1)
        self.assertEqual(result["bytes"], sum(map(len, self.snapshot(self.output).values())))

    def test_repeated_build_replaces_only_known_generated_output(self):
        self.build()
        (self.web / "app.js").write_text("updated application")
        self.build()
        self.assertEqual((self.output / "app.js").read_text(), "updated application")
        (self.output / "private-note.txt").write_text("do not delete")
        with self.assertRaisesRegex(ValueError, "unexpected content"):
            self.build()
        self.assertEqual((self.output / "private-note.txt").read_text(), "do not delete")

    def test_invalid_input_preserves_the_previous_site(self):
        self.build()
        before = self.snapshot(self.output)
        self.bundle["audio"]["sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.build()
        self.assertEqual(before, self.snapshot(self.output))

    def test_unlisted_file_in_examples_is_rejected(self):
        (self.examples / "private-recording.wav").write_bytes(b"recording")
        with self.assertRaisesRegex(ValueError, "Unlisted"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_manifest_cannot_escape_the_examples_directory(self):
        for path in ("../private.ku100.json", "/absolute.ku100.json", "https://example.org/a.ku100.json", "nested/scene.ku100.json"):
            with self.subTest(path=path):
                self.manifest["examples"][0]["path"] = path
                self.save()
                with self.assertRaisesRegex(ValueError, "local"):
                    self.build()

    def test_duplicate_manifest_ids_and_paths_are_rejected(self):
        entry = deepcopy(self.manifest["examples"][0])
        self.manifest["examples"].append(entry)
        self.save()
        with self.assertRaisesRegex(ValueError, "unique"):
            self.build()
        entry["id"] = "second"
        self.save()
        with self.assertRaisesRegex(ValueError, "unique"):
            self.build()

    def test_unknown_bundle_schema_or_manifest_fields_are_rejected(self):
        self.bundle["version"] = "ku100-render/2"
        self.save()
        with self.assertRaisesRegex(ValueError, "schema"):
            self.build()
        self.bundle["version"] = "ku100-render/1"
        self.manifest["tracking_url"] = "https://example.org"
        self.save()
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.build()

    def test_malformed_numeric_trace_contracts_fail(self):
        variants = [
            {"columns": ["time_s", "time_s"], "rows": [[0, 0]]},
            {"columns": ["time_s", "force"], "rows": [[0]]},
            {"columns": ["time_s", "force"], "rows": [[0, float("nan")]]},
            {"columns": ["time_s", "force"], "rows": [[0, True]]},
        ]
        for trace in variants:
            with self.subTest(trace=trace):
                self.bundle["trace"] = trace
                self.save()
                with self.assertRaises(ValueError):
                    self.build()

    def test_duplicate_json_keys_and_overflowing_numbers_are_rejected(self):
        path = self.examples / "index.json"
        text = path.read_text()
        for malformed in (text.replace('"version": 1', '"version": 1, "version": 1'), text.replace('"version": 1', '"version": 1e999')):
            with self.subTest(malformed=malformed[:40]):
                path.write_text(malformed)
                with self.assertRaises(ValueError):
                    self.build()

    def test_audio_metadata_hash_channels_and_duration_are_enforced(self):
        original = deepcopy(self.bundle)
        for field, value in (("sample_rate_hz", 44100), ("duration_s", 1), ("duration_s", True)):
            with self.subTest(field=field, value=value):
                self.bundle = deepcopy(original)
                self.bundle[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.build()
        for key, value in (("channels", 1), ("channels", True), ("sha256", "0" * 64), ("base64", "%%%")):
            with self.subTest(key=key):
                self.bundle = deepcopy(original)
                self.bundle["audio"][key] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.build()

    def test_corrupt_or_nonfinite_wav_cannot_pass_with_a_fresh_hash(self):
        original = base64.b64decode(self.bundle["audio"]["base64"])
        nonfinite = bytearray(original)
        struct.pack_into("<f", nonfinite, 44, float("nan"))
        for raw in (original + b"extra", original[:-1], bytes(nonfinite)):
            with self.subTest(length=len(raw)):
                self.bundle["audio"]["base64"] = base64.b64encode(raw).decode("ascii")
                self.bundle["audio"]["sha256"] = hashlib.sha256(raw).hexdigest()
                self.save()
                with self.assertRaises(ValueError):
                    self.build()

    def test_file_and_total_publication_caps_apply(self):
        with patch.object(build_site, "MAX_BUNDLE_BYTES", 64):
            with self.assertRaisesRegex(ValueError, "publication limit"):
                self.build()
        with patch.object(build_site, "MAX_SITE_BYTES", 64):
            with self.assertRaisesRegex(ValueError, "80 MiB"):
                self.build()
        self.assertFalse(self.output.exists())

    def test_source_and_output_overlap_is_rejected_including_dotdot_alias(self):
        for output in (self.web, self.root, self.web / "dist", self.root / "dist" / ".." / "web"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "separate"):
                    build_site.build_site(self.web, output)
        self.assertTrue((self.web / "index.html").is_file())

    def test_symlinked_application_is_never_copied(self):
        path = self.web / "app.js"
        path.unlink()
        secret = self.root / "private.js"
        secret.write_text("private sibling")
        path.symlink_to(secret)
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.build()

    def test_symlinked_output_or_ancestor_is_rejected(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "linked"
        link.symlink_to(real, target_is_directory=True)
        for output in (link, link / "dist"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "symbolic links"):
                    build_site.build_site(self.web, output)
        self.assertEqual(list(real.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
