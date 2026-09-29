"""A strict, portable scene contract shared by native and static workflows."""
from __future__ import annotations

import json
import math
from pathlib import Path


def _pairs(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise ValueError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def load_json(path: Path | str):
    def invalid(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=invalid)


def finite_number(value, name: str, *, integer=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be a finite number")
    if integer and value != int(value):
        raise ValueError(f"{name} must be an integer")
    return int(value) if integer else float(value)


def canonical_scene(raw: dict, physics_defaults: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("A scene must be a JSON object")
    allowed = {"version", "name", "preset", "side", "duration_s", "seed", "physics", "receiver", "capture"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError("Unknown scene fields: " + ", ".join(sorted(extra)))
    if raw.get("version") != "ku100-scene/1":
        raise ValueError("Scene version must be ku100-scene/1")
    name = raw.get("name", "Untitled physical scene")
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        raise ValueError("Scene name must be 1–160 characters")
    preset = raw.get("preset", "stroke")
    side = raw.get("side", "left")
    if preset not in ("stroke", "press", "tap", "silence") or side not in ("left", "right"):
        raise ValueError("Unsupported action or side")
    duration = finite_number(raw.get("duration_s", 4.0), "duration_s")
    if not 0.02 <= duration <= 30:
        raise ValueError("duration_s must be between 0.02 and 30 seconds")
    seed = finite_number(raw.get("seed", 1), "seed", integer=True)
    if not 0 <= seed <= 4294967295:
        raise ValueError("seed must be an unsigned 32-bit texture identity")
    defaults = {k: v for k, v in physics_defaults.items() if k not in {"duration_s", "action", "side", "seed"}}
    physics = raw.get("physics", {})
    if not isinstance(physics, dict) or set(physics) - set(defaults):
        raise ValueError("Unknown or malformed physics parameters")
    complete = {}
    integer_fields = {"sample_rate", "modes_per_plate", "trace_stride", "duct_cells", "unsteady_viscous_losses"}
    for key, default in defaults.items():
        complete[key] = finite_number(physics.get(key, default), "physics." + key, integer=key in integer_fields)
    # The pure physics core supports higher-rate probes, but exported scenes
    # must use the receiver/decimator's supported integration-rate range.
    rate = complete["sample_rate"]
    if not 48000 <= rate <= 768000 or rate % 48000:
        raise ValueError("Scene integration rate must be a multiple of 48 kHz up to 768 kHz")
    if "trace_stride" not in physics:
        complete["trace_stride"] = max(1, round(rate / 200))
    receiver = raw.get("receiver", {})
    if not isinstance(receiver, dict) or set(receiver) - {"mode", "azimuth_deg", "distance_m"}:
        raise ValueError("Unknown or malformed receiver parameters")
    mode = receiver.get("mode", "contact")
    if mode not in ("contact", "airborne"):
        raise ValueError("Only generic contact and measured KU100 airborne receivers are implemented")
    angle = finite_number(receiver.get("azimuth_deg", 90 if side == "left" else 270), "azimuth_deg") % 360
    if angle >= 360:
        angle = 0.0
    distance = finite_number(receiver.get("distance_m", 0.25), "distance_m")
    if not 0.25 <= distance <= 1.5:
        raise ValueError("The measured airborne receiver supports only 0.25–1.5 metres")
    capture_defaults = {"sensitivity_mv_pa": 20.0, "preamp_gain_db": 20.0, "adc_full_scale_v": 2.0}
    capture = raw.get("capture", {})
    if not isinstance(capture, dict) or set(capture) - set(capture_defaults):
        raise ValueError("Unknown or malformed capture parameters")
    capture = {k: finite_number(capture.get(k, v), "capture." + k) for k, v in capture_defaults.items()}
    return {"version": "ku100-scene/1", "name": name, "preset": preset, "side": side,
            "duration_s": duration, "seed": seed, "physics": complete,
            "receiver": {"mode": mode, "azimuth_deg": angle, "distance_m": distance}, "capture": capture}


def native_arguments(scene: dict) -> list[str]:
    args = ["--action", scene["preset"], "--side", scene["side"],
            "--duration-s", str(scene["duration_s"]), "--seed", str(scene["seed"])]
    for name, value in scene["physics"].items():
        args += ["--" + name.replace("_", "-"), str(value)]
    receiver = scene["receiver"]
    args += ["--receiver", receiver["mode"], "--azimuth-deg", str(receiver["azimuth_deg"]),
             "--distance-m", str(receiver["distance_m"])]
    for name, value in scene["capture"].items():
        args += ["--" + name.replace("_", "-"), str(value)]
    return args
