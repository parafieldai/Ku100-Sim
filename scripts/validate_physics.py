#!/usr/bin/env python3
"""Reproduce the native fixture's finite-state, energy and refinement probes.

The reported band-power fractions qualify each spectral comparison: weakly
excited high bands cannot substantiate a broadband fidelity claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[1]


def rms(x: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean(x * x, axis=0))


def validate(work: Path) -> dict:
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("A C++17 compiler is required")
    sources = [ROOT / "tests/physics_convergence_probe.cpp", ROOT / "native/physics.cpp"]
    binary = work / "probe"
    flags = ["-std=c++17", "-O3", "-Wall", "-Wextra", "-I" + str(ROOT / "native")]
    subprocess.run(shlex.split(compiler) + flags + list(map(str, sources)) + ["-o", str(binary)], check=True)
    raw = work / "raw"
    completed = subprocess.run([str(binary), str(raw)], check=True, text=True, capture_output=True)
    records = [json.loads(line) for line in completed.stdout.splitlines()]
    meta = {item["name"]: item for item in records}
    signals = {name: np.fromfile(raw / (name + ".f64"), dtype=np.float64).reshape(-1, 2)
               for name in meta}
    for name, signal in signals.items():
        if not np.isfinite(signal).all() or len(signal) != meta[name]["frames"]:
            raise AssertionError(f"Invalid physical pressure data: {name}")
    base = signals["base"]
    mirror_error = float(np.max(np.abs(base - signals["mirror"][:, ::-1])))
    silence = float(np.max(np.abs(signals["silence"])))
    zero_load = float(np.max(np.abs(signals["zero-load"])))
    if silence != 0 or zero_load != 0:
        raise AssertionError("A relaxed undriven fixture must be silent")
    if mirror_error > 1e-8:
        raise AssertionError("Symmetric fixture failed its ear-swap check")
    for row in records:
        if not row["regime_valid"]:
            raise AssertionError(f"Default fixture probe left its declared small-signal regime: {row['name']}")
        if row["loss_j"] < 0 or row["remaining_energy_j"] < 0:
            raise AssertionError(f"Negative physical energy: {row['name']}")
        if row["energy_residual_j"] > max(1e-10, abs(row["work_j"]) * 1e-8):
            raise AssertionError(f"Work-balance failure: {row['name']}")
        if row["force_residual_n"] > 1e-8:
            raise AssertionError(f"Unconverged contact force: {row['name']}")
    pairs = [("m64", "base"), ("base", "m256"), ("m256", "m512"),
             ("m512", "m1024"), ("d16", "base"), ("base", "d64"),
             ("d64", "d128"), ("r96", "base"), ("base", "r384")]
    comparisons = []
    for coarse, fine in pairs:
        x, y = signals[coarse], signals[fine]
        fs = meta[coarse]["rate"]
        # End-of-step observations share these exact physical sample times.
        factor = meta[fine]["rate"] // fs
        if factor > 1:
            y = y[factor - 1::factor]
        relative = rms(x - y) / rms(y)
        item = {"coarse": coarse, "fine": fine,
                "pressure_relative_l2": relative.tolist(), "bands": []}
        start, end = int(0.12 * fs), int(0.55 * fs)
        f, px = welch(x[start:end], fs=fs, nperseg=int(fs * 0.08), axis=0)
        _, py = welch(y[start:end], fs=fs, nperseg=int(fs * 0.08), axis=0)
        total = np.sum(py[(f >= 20) & (f < 4000)], axis=0)
        for low, high in [(20, 250), (250, 500), (500, 2000), (2000, 4000)]:
            mask = (f >= low) & (f < high)
            band = np.sum(py[mask], axis=0)
            item["bands"].append({
                "hz": [low, high],
                "relative_psd_l1": (np.sum(np.abs(px[mask] - py[mask]), axis=0)
                                    / np.maximum(band, 1e-300)).tolist(),
                "reference_fraction_of_20_4000hz_power": (band / total).tolist(),
                "reference_band_is_weak": bool(np.any(band / total < 1e-6)),
            })
        comparisons.append(item)
    modes = comparisons[:4]
    for previous, current in zip(modes, modes[1:]):
        if np.any(np.array(current["pressure_relative_l2"]) >= previous["pressure_relative_l2"]):
            raise AssertionError("This fixed trajectory did not converge under modal refinement")
    if max(comparisons[-1]["pressure_relative_l2"]) > 1e-3:
        raise AssertionError("192/384 kHz trajectory disagreement exceeds declared test bound")
    identity_files = sources + [ROOT / "native/physics.hpp", Path(__file__).resolve()]
    return {
        "version": "native-physics-convergence/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "compiler": subprocess.check_output(shlex.split(compiler) + ["--version"], text=True).splitlines()[0],
        "flags": flags,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in identity_files},
        "trajectory": {"duration_s": 0.8, "nominal_load_n": meta["base"]["load_n"], "spectral_interval_s": [0.12, 0.55],
                       "spectral_window_s": 0.08, "window": "Hann", "overlap": "50%",
                       "gain_or_normalization_applied": False},
        "mechanics_runs": records,
        "base_rms_pa": rms(base).tolist(),
        "mirror_max_abs_error_pa": mirror_error,
        "silence_max_abs_pa": silence,
        "zero_load_max_abs_pa": zero_load,
        "comparisons": comparisons,
        "numerical_checks_passed": True,
        "device_calibration_established": False,
        "wet_contact_realism_established": False,
        "broadband_fidelity_established": False,
        "limitations": [
            "Generic paired plate/chamber/duct fixture, not measured KU100 internals",
            "Default source is strongly dominated by power below 500 Hz",
            "Weak high-band excitation cannot prove high-band convergence or realism",
            "Raw chamber pressure is not calibrated pressure at a real microphone capsule",
            "Only these finite-duration trajectories and declared parameter values were assessed",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "validation/physics-convergence.json")
    parser.add_argument("--keep-work", type=Path, help="Keep compiled probe and raw double pressures here")
    args = parser.parse_args()
    if args.keep_work:
        args.keep_work.mkdir(parents=True, exist_ok=False)
        report = validate(args.keep_work.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="ku100-physics-") as directory:
            report = validate(Path(directory))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "report": str(args.out),
                      "broadband_fidelity_established": False}))


if __name__ == "__main__":
    main()
