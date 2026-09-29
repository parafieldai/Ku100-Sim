#!/usr/bin/env python3
"""Render a scene in native C++, verify the WAV and export a portable viewer bundle."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ku100sim.audio import describe, read_wav
from ku100sim.scene import canonical_scene, load_json, native_arguments
from build_native import build


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_identity():
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "native").glob("*"))
            if p.suffix in (".cpp", ".hpp")}


def ensure_binary(path: Path | None) -> tuple[Path, dict]:
    selected = path or ROOT / "build" / "ku100-native"
    receipt = selected.with_suffix(".build.json")
    current = source_identity()
    if path is None and (not selected.is_file() or not receipt.is_file()
                         or load_json(receipt).get("source_sha256") != current):
        selected = build()
    if not selected.is_file():
        raise ValueError("Native executable is missing")
    if receipt.is_file():
        record = load_json(receipt)
        if record.get("binary_sha256") != digest(selected) or record.get("source_sha256") != current:
            raise ValueError("Native binary/source identity mismatch; rebuild before rendering")
    else:
        raise ValueError("Native binary lacks a build identity; build it with scripts/build_native.py")
    return selected.resolve(), record


def git_identity():
    try:
        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip())
        return {"commit": head, "working_tree_modified": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_modified": None}


def render(scene_path: Path, destination: Path, *, binary: Path | None = None,
           bank: Path | None = None) -> dict:
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Output already exists; choose a new output directory")
    executable, build_record = ensure_binary(binary)
    description = json.loads(subprocess.check_output([str(executable), "--describe"], text=True))
    scene = canonical_scene(load_json(scene_path), description["physics_defaults"])
    selected_bank = (bank or ROOT / "data" / "ku100_bank.bin").resolve()
    if scene["receiver"]["mode"] == "airborne" and not selected_bank.is_file():
        raise ValueError("Measured KU100 bank missing. Run python scripts/prepare_ku100.py first.")
    bank_identity = None
    if scene["receiver"]["mode"] == "airborne":
        expected = load_json(ROOT / "data" / "manifest.json")
        bank_identity = digest(selected_bank)
        if bank_identity != expected.get("sha256") or selected_bank.stat().st_size != expected.get("bytes"):
            raise ValueError("HRIR bank differs from the verified KU100 source manifest; rebuild it with scripts/prepare_ku100.py")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ku100-render-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "result"
        command = [str(executable), "--out", str(stage)] + native_arguments(scene)
        if scene["receiver"]["mode"] == "airborne":
            command += ["--bank", str(selected_bank)]
        started = time.monotonic()
        process = subprocess.run(command, capture_output=True, text=True, timeout=1800)
        elapsed = time.monotonic() - started
        if process.returncode:
            raise RuntimeError(process.stderr.strip() or "Native renderer failed")
        native = load_json(stage / "native.json")
        rate, samples = read_wav(stage / "render.wav")
        metrics = describe(rate, samples)
        if metrics["frames"] != native["frames"] or rate != 48000:
            raise RuntimeError("Native report and exported WAV disagree")
        if native["physics"].get("finite") is not True:
            raise RuntimeError("Native mechanics reported invalid state")
        for value in native["physics"].values():
            if isinstance(value, (int, float)) and not math.isfinite(value):
                raise RuntimeError("Non-finite physics evidence")
        metrics["physics"] = native["physics"]
        metrics["render_wall_seconds"] = elapsed
        metrics["digital_gain_per_pa"] = native["digital_gain_per_pa"]
        with (stage / "trace.csv").open(newline="") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            rows = [[float(row[key]) for key in columns] for row in reader]
        if not rows or any(not math.isfinite(v) for row in rows for v in row):
            raise RuntimeError("Missing or non-finite native trace")
        # These positions depict the solved fixed footprint and normal indentation.
        # The texture translates through it; we never animate an unsolved moving
        # load across the plate and imply that it drove the generated waveform.
        indent_index = columns.index("indentation_m")
        columns += ["simulation_time_s", "actuator_x_m", "actuator_y_m", "actuator_z_m"]
        side = 1 if scene["side"] == "left" else -1
        latency = native["decimation_latency_s"] + native["fractional_delay_latency_s"] + native["modeled_propagation_delay_s"]
        for row in rows:
            original_time = row[0]
            # C++ sample zero is the first completed integration step, played
            # at WAV time zero before causal receiver/filter latency.
            row[0] += latency - native["simulation_first_sample_s"]
            row += [original_time, 0.0, side * (0.0875 + scene["physics"]["contact_radius_m"] - row[indent_index]), 0.0]
        if len(rows) > 6000:
            stride = math.ceil(len(rows) / 6000)
            kept = rows[::stride]
            if kept[-1] != rows[-1]:
                kept.append(rows[-1])
            rows = kept
        geometry = {
            "units": "m", "axes": {"x": "forward", "y": "left", "z": "up"},
            "head": {"radii_m": [0.09, 0.075, 0.11], "center_m": [0, 0, 0]},
            "ears": [{"side": "left", "center_m": [0, 0.0875, 0]}, {"side": "right", "center_m": [0, -0.0875, 0]}],
            "contact": {"side": scene["side"], "patch_radius_m": scene["physics"]["contact_radius_m"],
                        "model": "Fixed footprint with translating analytic microtexture"},
            "label": "Generic bilateral physical fixture; this is not a KU100 scan or measured material model",
        }
        wav = (stage / "render.wav").read_bytes()
        source_map = source_identity()
        provenance = {
            **git_identity(), "renderer": "native-cpp-physics", "build": build_record,
            "native_source_sha256": source_map,
            "native_source_digest": hashlib.sha256(json.dumps(source_map, sort_keys=True).encode()).hexdigest(),
            "scene_sha256": hashlib.sha256(json.dumps(scene, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "reference_recording_used_at_runtime": False, "absolute_device_calibration": False,
            "human_listening_assessment": "not performed",
            "receiver": native["source_observation"],
            "hrir_bank_sha256": bank_identity,
            "capture_mapping": "Declared nominal pressure-to-voltage scalar; the generic chambers and airborne bank are not absolutely calibrated target-device capsule pressures",
            "latency": {key: native[key] for key in ("simulation_first_sample_s", "decimation_latency_s", "fractional_delay_latency_s", "modeled_propagation_delay_s", "published_hrir_time_origin_preserved")},
        }
        bundle = {"version": "ku100-render/1", "scene": scene,
                  "audio": {"mime": "audio/wav", "base64": base64.b64encode(wav).decode("ascii"),
                            "sha256": hashlib.sha256(wav).hexdigest(), "channels": 2},
                  "sample_rate_hz": rate, "duration_s": len(samples) / rate,
                  "metrics": metrics, "trace": {"columns": columns, "rows": rows},
                  "geometry": geometry, "provenance": provenance}
        (stage / "scene.json").write_text(json.dumps(scene, indent=2, allow_nan=False) + "\n")
        (stage / "render.ku100.json").write_text(json.dumps(bundle, separators=(",", ":"), allow_nan=False) + "\n")
        report = {k: v for k, v in bundle.items() if k not in ("audio", "trace")}
        report["audio_sha256"] = bundle["audio"]["sha256"]
        report["trace_rows"] = len(rows)
        (stage / "render.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        stage.rename(destination)
    return {"ok": True, "output": str(destination), "wav": str(destination / "render.wav"),
            "bundle": str(destination / "render.ku100.json"), "metrics": metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--bank", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.scene, args.out, binary=args.binary, bank=args.bank), allow_nan=False))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
