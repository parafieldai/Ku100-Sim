"""Independent scene -> native renderer -> Float32 WAV -> bundle checks.

Run: python -m unittest discover -s tests -p test_pipeline.py -v

The native executable, scenes and outputs are built in a temporary directory.
No reference audio, model service, network access or repository-source mutation
is needed. SciPy reads the WAV independently of ku100sim.audio.
"""
from __future__ import annotations

import base64
import copy
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ku100sim.scene import canonical_scene, load_json  # noqa: E402


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fixture(**overrides) -> dict:
    scene = {
        "version": "ku100-scene/1", "name": "Pipeline audit fixture",
        "preset": "stroke", "side": "left", "duration_s": .2, "seed": 411,
        "physics": {"modes_per_plate": 128}, "receiver": {"mode": "contact"},
    }
    scene.update(overrides)
    return scene


class NativePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="ku100-pipeline-audit-")
        cls.work = Path(cls.temporary.name)
        cls.binary = cls.work / "ku100-native"
        built = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_native.py"), "--out", str(cls.binary)],
            cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
        if built.returncode:
            cls.temporary.cleanup()
            raise RuntimeError("Native pipeline audit build failed:\n" + built.stderr)
        cls.build = json.loads(cls.binary.with_suffix(".build.json").read_text())
        described = subprocess.run([str(cls.binary), "--describe"], capture_output=True,
                                   text=True, timeout=10, check=True)
        cls.defaults = json.loads(described.stdout)["physics_defaults"]
        cls.serial = 0
        cls.cached_contact = None
        cls.observations = {"build": cls.build, "duration_s": .2, "renders": {}}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def next_path(self, label: str) -> Path:
        type(self).serial += 1
        return self.work / f"{self.serial:03d}-{label}"

    def call_python(self, raw=None, *, text=None, destination=None, binary=None,
                    bank=None, rejected=False):
        source = self.next_path("scene.json")
        source.write_text(text if text is not None else json.dumps(raw), encoding="utf-8")
        destination = destination or self.next_path("render")
        command = [sys.executable, str(ROOT / "scripts/render.py"), "--scene", str(source),
                   "--out", str(destination), "--binary", str(binary or self.binary)]
        if bank is not None:
            command += ["--bank", str(bank)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                timeout=90, check=False)
        if rejected:
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(result.stdout.strip(), result.stdout)
            # A traceback is not the CLI's documented structured error response.
            error = json.loads(result.stderr)
            self.assertIs(error.get("ok"), False)
            self.assertIsInstance(error.get("error"), str)
            self.assertTrue(error["error"])
            return destination, error
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        status = json.loads(result.stdout)
        self.assertIs(status["ok"], True)
        self.assertEqual(Path(status["output"]), destination.resolve())
        bundle = json.loads((destination / "render.ku100.json").read_text())
        native = json.loads((destination / "native.json").read_text())
        rate, samples = wavfile.read(destination / "render.wav")
        self.assertEqual(rate, 48000)
        self.assertEqual(samples.dtype, np.dtype("float32"))
        self.assertEqual(samples.ndim, 2)
        self.assertEqual(samples.shape[1], 2)
        self.assertTrue(np.isfinite(samples).all())
        return {"path": destination, "status": status, "bundle": bundle,
                "native": native, "samples": samples}

    def contact(self):
        if type(self).cached_contact is None:
            # The contact route must work without measured airborne data.
            type(self).cached_contact = self.call_python(
                fixture(), bank=self.work / "intentionally-absent-bank.bin")
            rendered = type(self).cached_contact
            self.observations["renders"]["contact"] = {
                "audio_sha256": rendered["bundle"]["audio"]["sha256"],
                "frames": len(rendered["samples"]),
                "rms_dbfs": rendered["bundle"]["metrics"]["rms_dbfs"],
                "peak_dbfs": rendered["bundle"]["metrics"]["peak_dbfs"],
                "digital_gain_per_pa": rendered["native"]["digital_gain_per_pa"],
                "physics": rendered["native"]["physics"],
            }
        return type(self).cached_contact

    def assert_unpublished(self, destination: Path):
        self.assertFalse(destination.exists())
        self.assertFalse(list(destination.parent.glob(".ku100-render-*")))

    def test_build_receipt_identifies_actual_executable_and_all_native_sources(self):
        expected = {str(p.relative_to(ROOT)): sha(p.read_bytes())
                    for p in (ROOT / "native").iterdir() if p.suffix in {".cpp", ".hpp"}}
        self.assertEqual(self.build["source_sha256"], expected)
        self.assertEqual(self.build["binary_sha256"], sha(self.binary.read_bytes()))
        self.assertIs(self.build["sanitizers"], False)
        self.assertIn("-std=c++17", self.build["flags"])

    def test_contact_wav_metrics_and_bundle_reproduce_the_same_raw_audio(self):
        rendered = self.contact()
        folder, bundle, native, samples = (
            rendered[k] for k in ("path", "bundle", "native", "samples"))
        body = (folder / "render.wav").read_bytes()
        self.assertEqual(bundle["version"], "ku100-render/1")
        self.assertEqual(bundle["audio"]["channels"], 2)
        self.assertEqual(base64.b64decode(bundle["audio"]["base64"], validate=True), body)
        self.assertEqual(bundle["audio"]["sha256"], sha(body))
        report = json.loads((folder / "render.json").read_text())
        self.assertEqual(report["audio_sha256"], sha(body))
        self.assertEqual(native["frames"], len(samples))
        self.assertEqual(bundle["metrics"]["frames"], len(samples))
        self.assertEqual(bundle["duration_s"], len(samples) / 48000)
        self.assertFalse(bundle["metrics"]["silent"])
        self.assertGreater(float(np.linalg.norm(samples[:, 0])), 0)
        self.assertGreater(float(np.linalg.norm(samples[:, 1])), 0)
        # Full causal decimator tail is exported, not cut at the action endpoint.
        count = math.ceil(bundle["scene"]["duration_s"] * bundle["scene"]["physics"]["sample_rate"])
        factor = bundle["scene"]["physics"]["sample_rate"] // 48000
        expected_frames = count if factor == 1 else (count + 128 * factor - 1) // factor + 1
        self.assertEqual(len(samples), expected_frames)
        values = samples.astype(np.float64)
        expected_rms = 20 * np.log10(np.sqrt(np.mean(values * values, axis=0)))
        np.testing.assert_allclose(bundle["metrics"]["rms_dbfs"], expected_rms, atol=1e-12)
        self.assertEqual(bundle["metrics"]["decoded_float64_sha256"], sha(values.astype("<f8").tobytes()))
        raw_rate, pressure = wavfile.read(folder / "cavity-pressure.wav")
        self.assertEqual(raw_rate, 48000)
        capture = bundle["scene"]["capture"]
        expected_gain = capture["sensitivity_mv_pa"] * .001 * 10 ** (capture["preamp_gain_db"] / 20) / capture["adc_full_scale_v"]
        self.assertAlmostEqual(native["digital_gain_per_pa"], expected_gain, places=16)
        np.testing.assert_allclose(samples, pressure.astype(float) * expected_gain,
                                   rtol=2e-7, atol=1e-12)
        trace = bundle["trace"]
        rows = np.array(trace["rows"])
        self.assertEqual(rows.shape[1], len(trace["columns"]))
        self.assertTrue(np.isfinite(rows).all())
        self.assertTrue(np.all(np.diff(rows[:, 0]) > 0))
        simulation = rows[:, trace["columns"].index("simulation_time_s")]
        latency = sum(native[k] for k in ("decimation_latency_s", "fractional_delay_latency_s",
                                         "modeled_propagation_delay_s"))
        np.testing.assert_allclose(rows[:, 0] - simulation,
                                   latency - native["simulation_first_sample_s"], atol=1e-15)
        self.assertAlmostEqual(simulation[-1], bundle["scene"]["duration_s"], places=12)
        self.assertEqual(bundle["geometry"]["axes"], {"x": "forward", "y": "left", "z": "up"})

    def test_portable_bundle_is_self_contained_and_records_verifiable_provenance(self):
        rendered = self.contact()
        portable = self.next_path("portable")
        portable.mkdir()
        copy_path = portable / "standalone.ku100.json"
        shutil.copy2(rendered["path"] / "render.ku100.json", copy_path)
        bundle = json.loads(copy_path.read_text())
        audio = base64.b64decode(bundle["audio"]["base64"], validate=True)
        rate, samples = wavfile.read(BytesIO(audio))
        self.assertEqual(rate, 48000)
        np.testing.assert_array_equal(samples, rendered["samples"])
        self.assertEqual(sorted(p.name for p in portable.iterdir()), [copy_path.name])
        provenance = bundle["provenance"]
        self.assertEqual(provenance["renderer"], "native-cpp-physics")
        self.assertEqual(provenance["build"], self.build)
        self.assertEqual(provenance["native_source_sha256"], self.build["source_sha256"])
        expected_source_digest = sha(json.dumps(self.build["source_sha256"], sort_keys=True).encode())
        self.assertEqual(provenance["native_source_digest"], expected_source_digest)
        expected_scene_digest = sha(json.dumps(bundle["scene"], sort_keys=True, separators=(",", ":")).encode())
        self.assertEqual(provenance["scene_sha256"], expected_scene_digest)
        self.assertIs(provenance["reference_recording_used_at_runtime"], False)
        self.assertIs(provenance["absolute_device_calibration"], False)
        self.assertIsNone(provenance["hrir_bank_sha256"])
        self.assertIn("commit", provenance)
        self.assertIn("working_tree_modified", provenance)
        self.assertEqual(provenance["human_listening_assessment"], "not performed")

    def test_real_render_bundle_passes_static_publication_validation(self):
        from scripts.build_site import _validate_bundle
        path = self.contact()["path"] / "render.ku100.json"
        _validate_bundle(path.read_bytes(), path.name)

    def test_same_scene_is_byte_deterministic_for_audio_trace_and_native_evidence(self):
        first = self.contact()
        second = self.call_python(fixture())
        for filename in ("render.wav", "cavity-pressure.wav", "airborne-source.wav", "trace.csv", "native.json", "scene.json"):
            with self.subTest(artifact=filename):
                self.assertEqual((first["path"] / filename).read_bytes(), (second["path"] / filename).read_bytes())
        self.assertEqual(first["bundle"]["provenance"]["scene_sha256"], second["bundle"]["provenance"]["scene_sha256"])
        # Runtime duration is observational metadata and is deliberately excluded.
        self.observations["deterministic_artifacts"] = 6

    def test_capture_uses_one_declared_gain_and_preserves_over_full_scale_values(self):
        first = self.contact()
        boosted = self.call_python(fixture(capture={"preamp_gain_db": 100.0}))
        for filename in ("cavity-pressure.wav", "airborne-source.wav", "trace.csv"):
            self.assertEqual((first["path"] / filename).read_bytes(), (boosted["path"] / filename).read_bytes())
        initial_gain_db = first["bundle"]["scene"]["capture"]["preamp_gain_db"]
        ratio = 10 ** ((100 - initial_gain_db) / 20)
        expected = first["samples"].astype(float) * ratio
        np.testing.assert_allclose(boosted["samples"], expected, rtol=2e-7, atol=1e-8)
        count = int(np.count_nonzero(np.abs(boosted["samples"]) > 1))
        self.assertGreater(count, 0)
        self.assertEqual(boosted["bundle"]["metrics"]["samples_above_full_scale"], count)
        self.assertGreater(float(np.max(np.abs(boosted["samples"]))), 1.0)
        self.assertAlmostEqual(first["bundle"]["metrics"]["left_minus_right_db"],
                               boosted["bundle"]["metrics"]["left_minus_right_db"], places=5)
        self.observations["capture"] = {"common_gain_ratio": ratio, "samples_above_full_scale": count,
                                        "unclipped_peak": float(np.max(np.abs(boosted["samples"])))}

    def test_load_control_changes_solved_motion_and_audio(self):
        baseline = self.contact()
        baseline_load = baseline["bundle"]["scene"]["physics"]["load_n"]
        changed_load = baseline_load / 2
        changed = self.call_python(fixture(physics={"modes_per_plate": 128, "load_n": changed_load}))
        self.assertNotEqual(baseline["bundle"]["audio"]["sha256"], changed["bundle"]["audio"]["sha256"])
        relative = float(np.linalg.norm(changed["samples"] - baseline["samples"]) /
                         np.linalg.norm(baseline["samples"]))
        self.assertGreater(relative, .01)
        old_force = baseline["native"]["physics"]["max_normal_force_n"]
        new_force = changed["native"]["physics"]["max_normal_force_n"]
        self.assertGreater(abs(old_force - new_force), .01 * old_force)
        self.observations["load_control"] = {"baseline_load_n": baseline_load, "changed_load_n": changed_load,
                                              "relative_audio_l2_change": relative,
                                              "max_normal_forces_n": [old_force, new_force]}

    def test_mirrored_contact_swaps_ears_without_independent_gain_matching(self):
        left = self.contact()
        right = self.call_python(fixture(side="right"))
        expected = left["samples"][:, ::-1]
        np.testing.assert_allclose(right["samples"], expected, rtol=2e-6, atol=1e-9)
        relative = float(np.linalg.norm(right["samples"] - expected) / np.linalg.norm(expected))
        self.assertLess(relative, 2e-6)
        self.observations["mirror_relative_audio_l2_error"] = relative
        left_y = np.array(left["bundle"]["trace"]["rows"])[:, -2]
        right_y = np.array(right["bundle"]["trace"]["rows"])[:, -2]
        np.testing.assert_allclose(left_y, -right_y, atol=1e-12)

    def test_silence_is_exact_zero_with_null_decibels_and_zero_work(self):
        rendered = self.call_python(fixture(preset="silence", duration_s=.15))
        for name in ("render.wav", "cavity-pressure.wav", "airborne-source.wav"):
            rate, samples = wavfile.read(rendered["path"] / name)
            self.assertEqual(rate, 48000)
            self.assertEqual(np.count_nonzero(samples), 0)
        metrics = rendered["bundle"]["metrics"]
        self.assertIs(metrics["silent"], True)
        self.assertEqual(metrics["rms_dbfs"], [None, None])
        self.assertEqual(metrics["peak_dbfs"], [None, None])
        self.assertEqual(metrics["samples_above_full_scale"], 0)
        for name in ("actuator_work_j", "dissipated_energy_j", "final_energy_j"):
            self.assertEqual(rendered["native"]["physics"][name], 0.0)
        self.observations["silence"] = {"exact_zero": True, "frames": len(rendered["samples"])}

    def test_measured_airborne_path_matches_exported_source_and_bank_without_extra_gain(self):
        bank = ROOT / "data/ku100_bank.bin"
        if not bank.is_file():
            self.skipTest("Prepare data/ku100_bank.bin for the measured-bank integration case")
        scene = fixture(preset="tap", receiver={"mode": "airborne", "azimuth_deg": 90, "distance_m": .5})
        rendered = self.call_python(scene, bank=bank)
        body = bank.read_bytes()
        magic, rate, rings, directions, taps = struct.unpack_from("<8s4I", body)
        self.assertEqual((magic, rate, directions), (b"KUHRIR01", 48000, 360))
        radii = np.frombuffer(body, dtype="<f8", count=rings, offset=24)
        ir = np.frombuffer(body, dtype="<f4", offset=24 + rings * 8).reshape(rings, directions, 2, taps)
        ring = int(np.flatnonzero(radii == .5)[0])
        _, source = wavfile.read(rendered["path"] / "airborne-source.wav")
        delay = .5 / rendered["bundle"]["scene"]["physics"]["sound_speed_m_s"] * rate
        whole = math.floor(delay)
        fraction = delay - whole
        kernel = np.sinc(np.arange(63) - 31 - fraction) * signal.windows.kaiser(63, 9.0, sym=True)
        kernel /= kernel.sum()
        delayed = np.pad(np.convolve(source[:, 0].astype(float), kernel), (whole, 0))
        expected = np.column_stack([np.convolve(delayed, ir[ring, 90, ear].astype(float))
                                    for ear in (0, 1)]) * rendered["native"]["digital_gain_per_pa"]
        self.assertEqual(rendered["samples"].shape, expected.shape)
        relative = float(np.linalg.norm(rendered["samples"] - expected) / np.linalg.norm(expected))
        self.assertLess(relative, 2e-6)
        self.assertEqual(rendered["bundle"]["provenance"]["hrir_bank_sha256"], sha(body))
        self.assertEqual(rendered["native"]["fractional_delay_latency_s"], 31 / 48000)
        self.assertIs(rendered["native"]["published_hrir_time_origin_preserved"], True)
        self.assertGreater(len(rendered["samples"]), len(source))
        self.observations["airborne"] = {"relative_independent_signal_l2_error": relative,
            "bank_sha256": sha(body), "frames": len(rendered["samples"]),
            "rms_dbfs": rendered["bundle"]["metrics"]["rms_dbfs"],
            "gain_per_pa": rendered["native"]["digital_gain_per_pa"]}

    def test_python_contract_rejects_wrong_types_unknown_fields_and_fractional_integers(self):
        cases = [None, [], True, 12, "scene"]
        changes = [("unknown", 1), ("version", True), ("name", ""), ("side", "both"),
                   ("preset", "recording"), ("duration_s", True), ("duration_s", "0.2"),
                   ("duration_s", float("nan")), ("seed", False), ("seed", 1.25),
                   ("seed", -1), ("seed", 4294967296), ("seed", 10**1000),
                   ("physics", []), ("physics", {"monitor_gain_db": 3}),
                   ("physics", {"load_n": True}), ("physics", {"sample_rate": 192000.5}),
                   ("physics", {"modes_per_plate": 128.5}), ("physics", {"trace_stride": 1.5}),
                   ("physics", {"duct_cells": 32.5}), ("physics", {"load_n": float("inf")}),
                   ("receiver", {"mode": "recording"}), ("receiver", {"azimuth_deg": False}),
                   ("receiver", {"distance_m": .1}), ("receiver", {"unknown": 0}),
                   ("capture", {"preamp_gain_db": True}), ("capture", {"normalize": True})]
        for key, value in changes:
            scene = fixture()
            scene[key] = value
            cases.append(scene)
        for index, scene in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    canonical_scene(scene, self.defaults)
        self.observations["canonical_rejections"] = len(cases)

    def test_json_loader_rejects_malformed_duplicates_and_nonfinite_constants(self):
        texts = ["{", "[] trailing", '{"version":"ku100-scene/1","duration_s":NaN}',
                 '{"version":"ku100-scene/1","duration_s":Infinity}',
                 '{"seed":1,"seed":2}', '{"physics":{"load_n":1,"load_n":2}}',
                 '{"seed":1,"\\u0073eed":2}']
        for index, text in enumerate(texts):
            with self.subTest(case=index):
                path = self.next_path("invalid.json")
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_json(path)
        self.observations["json_rejections"] = len(texts)

    def test_python_cli_rejects_invalid_inputs_structurally_without_publishing(self):
        cases = ["{", '{"version":"ku100-scene/1","seed":1,"seed":2}',
                 '{"version":"ku100-scene/1","duration_s":NaN}',
                 '{"version":"ku100-scene/1","duration_s":1e999}',
                 json.dumps(fixture(seed=10**1000)), json.dumps(fixture(duration_s=True)),
                 json.dumps(fixture(physics={"modes_per_plate": 2.5})),
                 json.dumps(fixture(physics={"load_n": -.2})),
                 json.dumps(fixture(capture={"adc_full_scale_v": 0})),
                 json.dumps(fixture(unknown_parameter=1))]
        for index, text in enumerate(cases):
            with self.subTest(case=index):
                destination, _ = self.call_python(text=text, rejected=True)
                self.assert_unpublished(destination)
        self.observations["python_cli_rejections"] = len(cases)

    def test_native_cli_rejects_unknown_duplicate_nonfinite_bool_and_fractional_controls(self):
        cases = [["--unknown", "1"], ["--load-n", ".1", "--load-n", ".2"],
                 ["--duration-s", "nan"], ["--load-n", "inf"], ["--load-n", "true"],
                 ["--modes-per-plate", "2.5"], ["--seed", "1.5"], ["--sample-rate", "44100"],
                 ["--side", "both"], ["--seed", "4294967296"]]
        for index, args in enumerate(cases):
            with self.subTest(case=index):
                destination = self.next_path("native-rejected")
                process = subprocess.run([str(self.binary), "--out", str(destination), *args],
                                         capture_output=True, text=True, timeout=10, check=False)
                self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                self.assertIs(json.loads(process.stderr)["ok"], False)
                self.assertFalse(destination.exists())
        self.observations["native_cli_rejections"] = len(cases)

    def test_existing_output_is_not_overwritten_by_either_entrypoint(self):
        rendered = self.contact()
        folder = rendered["path"]
        before = {p.name: sha(p.read_bytes()) for p in folder.iterdir() if p.is_file()}
        _, error = self.call_python(fixture(), destination=folder, rejected=True)
        self.assertIn("already exists", error["error"])
        native = subprocess.run([str(self.binary), "--out", str(folder), "--duration-s", ".15"],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(native.returncode, 2, native.stderr)
        self.assertIn("refusing to overwrite", json.loads(native.stderr)["error"])
        self.assertEqual(before, {p.name: sha(p.read_bytes()) for p in folder.iterdir() if p.is_file()})
        empty = self.next_path("empty-existing")
        empty.mkdir()
        self.call_python(fixture(), destination=empty, rejected=True)
        self.assertEqual(list(empty.iterdir()), [])

    def test_missing_or_corrupt_measured_bank_fails_without_fallback_or_partial_bundle(self):
        scene = fixture(receiver={"mode": "airborne", "distance_m": .5})
        destination, error = self.call_python(scene, bank=self.work / "missing-bank.bin", rejected=True)
        self.assertIn("bank missing", error["error"])
        self.assert_unpublished(destination)
        broken = self.next_path("truncated-bank.bin")
        broken.write_bytes(b"KUHRIR01")
        destination, _ = self.call_python(scene, bank=broken, rejected=True)
        self.assert_unpublished(destination)
        bank = ROOT / "data/ku100_bank.bin"
        if bank.is_file():
            altered = self.next_path("structurally-valid-but-unverified-bank.bin")
            content = bytearray(bank.read_bytes())
            content[-4] ^= 1  # a finite Float32 mantissa bit, leaving the entire layout intact
            altered.write_bytes(content)
            destination, error = self.call_python(scene, bank=altered, rejected=True)
            self.assertIn("source manifest", error["error"])
            self.assert_unpublished(destination)

    def test_explicit_missing_unidentified_tampered_and_stale_binaries_are_rejected(self):
        destination, _ = self.call_python(fixture(), binary=self.work / "missing-binary", rejected=True)
        self.assert_unpublished(destination)
        for kind in ("no-receipt", "tampered-binary", "stale-source"):
            with self.subTest(case=kind):
                binary = self.next_path(kind)
                shutil.copy2(self.binary, binary)
                receipt = copy.deepcopy(self.build)
                if kind != "no-receipt":
                    if kind == "tampered-binary":
                        with binary.open("ab") as handle:
                            handle.write(b"audit tamper fixture")
                    if kind == "stale-source":
                        receipt["source_sha256"]["native/physics.cpp"] = "0" * 64
                    binary.with_suffix(".build.json").write_text(json.dumps(receipt))
                destination, error = self.call_python(fixture(), binary=binary, rejected=True)
                self.assertIn("identity", error["error"])
                self.assert_unpublished(destination)


if __name__ == "__main__":
    unittest.main(verbosity=2)
