#!/usr/bin/env python3
"""Prepare the corrected native KU100 bank from the authors' pinned SOFA release.

Requires numpy, scipy and h5py. No recordings, fitted noise or contact responses
are synthesized. Downloaded originals remain in --source-dir, outside the repo.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import urllib.request
import zipfile

import h5py
import numpy as np
from scipy.signal import correlate, correlation_lags, resample_poly
from scipy.io import loadmat
from scipy.io.matlab._mio5 import MatFile5Reader

ROOT = Path(__file__).resolve().parents[1]
RECORD = "https://zenodo.org/records/4297951"
API = "https://zenodo.org/api/records/4297951/files/"
RADII = [0.25, 0.5, 0.75, 1.0, 1.5]
GAINS = [1.0, 0.33, 0.25, 0.16, 0.095]
FILES = {
    "NFHRIR_CIRC360_SOFA.zip": "b6ba22b8f575d038675c442f46fe0877a16cfd592681410a580141bd2b966173",
    "NF_Datasets_Gains_infos.pdf": "3b7884522e6c55e92fb71b0711c452a50d6019789d113dea5973d99269190bfb",
    "Arend_TMT2016.pdf": "ee17934870e116f6498882c6aa38f9f035f723bfe64deead8e0ceeebf66c1170",
    "NFHRIR_CIRC360_miro.zip": "2dfd2b0e176d5a418191ccad04f8f2cea34b9bb42bf697026e4163159add5974",
    "miro.m": "1ea7dd29b960f84174638cf672966b36deb6ddf2f0a0e1d5090c534bcb378026",
}
SOFA_HASHES = [
    "13e5be0e6f65926c6d43f704e40ef7413b7fb6bb366e842b708e141e43775b4e",
    "d7d03f9d264292fc3dd32a5ab7f493a4f66e8ae2ee3a8e8c7f54922675933012",
    "029a3e87d395d346b6df8789d7f9263f4b5b5ccef91b8cc4dc9b82f157dea167",
    "5b5b2450776e79d70f6ec1b196572a4c0fd7a58d79cbbca1be6cbadd298026ee",
    "7355b512dbfc826ca4b307f235126f0ea668ea06e67321f20a3a120acc3c4c14",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked(data: bytes, expected: str, name: str) -> bytes:
    actual = sha(data)
    if actual != expected:
        raise ValueError(f"{name}: SHA256 {actual}, expected {expected}")
    return data


def acquire(directory: Path, download: bool) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        target = directory / name
        if not target.exists():
            if not download:
                raise FileNotFoundError(f"{target}; pass --download to retrieve pinned originals")
            with urllib.request.urlopen(API + name + "/content", timeout=60) as response:
                content = checked(response.read(), digest, name)
            target.write_bytes(content)
        checked(target.read_bytes(), digest, name)
    paths = []
    with zipfile.ZipFile(directory / "NFHRIR_CIRC360_SOFA.zip") as archive:
        for radius, digest in zip(RADII, SOFA_HASHES):
            name = f"HRIR_CIRC360_NF{round(radius * 100):03d}.sofa"
            content = checked(archive.read(name), digest, name)
            target = directory / name
            if not target.exists() or sha(target.read_bytes()) != digest:
                target.write_bytes(content)
            paths.append(target)
    return paths


def txt(value) -> str:
    return bytes(value).decode("latin-1") if isinstance(value, (bytes, np.bytes_)) else str(value)


def verify_orientation(directory: Path, paths: list[Path]) -> dict:
    """Decode this hash-pinned legacy MCOS object; not a generic MATLAB reader.

    scipy's normal loadmat exposes but does not interpret this MCOS workspace.
    Reading its first matrix separately prevents a later unnamed workspace from
    replacing it. The positional fields below apply only to this pinned release.
    """
    class_text = (directory / "miro.m").read_text(encoding="latin-1")
    assert "left   = 'LEFT: AZ 90" in class_text
    assert "right  = 'RIGHT: AZ 270" in class_text
    checks = []
    with zipfile.ZipFile(directory / "NFHRIR_CIRC360_miro.zip") as archive:
        for path in paths:
            mat_name = path.with_suffix(".mat").name
            raw = archive.read(mat_name)
            workspace = loadmat(BytesIO(raw))["__function_workspace__"].tobytes()
            header = b"MATLAB 5.0 MAT-file".ljust(116, b" ") + b"\0" * 8 + b"\0\x01IM"
            reader = MatFile5Reader(BytesIO(header + workspace[8:]), squeeze_me=True, struct_as_record=False)
            reader.initialize_read()
            reader.read_file_header()
            h, _ = reader.read_var_header()
            values = reader.read_var_array(h).MCOS["arr"][0]
            assert values.shape == (48,) and values[2] == path.stem
            assert values[37] == "Left Ear" and values[38] == "Right Ear"
            assert values[46] == "DEG" and values[43] == 128
            left, right = values[39].T, values[40].T
            assert left.shape == right.shape == (360, 128)
            named = np.stack([left, right], axis=1).astype(np.float64)
            # Exact equations of miro_winHead and miro_winTail in miro.m.
            # The head function starts c at 1, unlike numpy.hanning's origin.
            head, tail = int(values[44]), int(values[45])
            window = np.ones(128)
            window[:head] = 0.5 + 0.5 * np.cos(2 * np.pi * (np.arange(1, head + 1) - (2 * head - 1) / 2) / (2 * head - 1))
            window[-tail:] = 0.5 + 0.5 * np.cos(2 * np.pi * (np.arange(tail, 2 * tail) - (2 * tail - 1) / 2) / (2 * tail - 1))
            with h5py.File(path) as source:
                assert np.array_equal(values[34], source["SourcePosition"][:, 0])
                delta = float(np.max(np.abs(source["Data.IR"][:] - named * window)))
                assert delta <= 1e-14, "SOFA no longer matches named MIRO channels"
            checks.append({"miro_file": mat_name, "miro_sha256": sha(raw), "sofa_file": path.name,
                           "miro_channel_labels": [values[37], values[38]], "miro_head_tail_window_taps": [head, tail],
                           "max_named_miro_getIR_vs_sofa_absolute_error": delta})
    return {"orientation_pass": True,
            "conclusion": "Keep SOFA channel0 as left, channel1 as right; azimuth90 is left,270 is right. No sample swapping or metadata rewriting.",
            "evidence": "Named MIRO Left Ear/Right Ear arrays, processed by authors' getIR head/tail windows, reproduce all archived SOFA coefficients. miroCoordinates in the accompanying class explicitly defines 90 left and270 right.",
            "receiver_position_issue": "SOFA ReceiverPosition signs conflict with that verified channel convention. Preserve the erroneous published positions in provenance, not as routing instructions.",
            "archive_sha256": FILES["NFHRIR_CIRC360_miro.zip"], "class_sha256": FILES["miro.m"],
            "decoder_scope": "Only hash-pinned original MCOS release; scipy.io.matlab._mio5 is an internal API used for this offline verification only.",
            "rings": checks}


def read_original(path: Path, radius: float) -> tuple[np.ndarray, dict]:
    with h5py.File(path, "r") as source:
        ir = source["Data.IR"][:]
        positions = source["SourcePosition"][:]
        if ir.shape != (360, 2, 128) or not np.isfinite(ir).all():
            raise ValueError(f"unsupported/nonfinite IR shape in {path}")
        if txt(source["SourcePosition"].attrs["Type"]) != "spherical":
            raise ValueError("expected spherical source coordinates")
        if txt(source["SourcePosition"].attrs["Units"]) != "degree, degree, metre":
            raise ValueError("unexpected source-coordinate units")
        if not np.array_equal(source["Data.SamplingRate"][:], [48000.0]):
            raise ValueError("48 kHz is required; no resampling is performed")
        if np.any(source["Data.Delay"][:] != 0):
            raise ValueError("nonzero SOFA Data.Delay needs explicit handling")
        if not np.allclose(positions[:, 1], 0, atol=1e-12) or not np.allclose(positions[:, 2], radius, atol=1e-12):
            raise ValueError("expected the requested horizontal circle")
        angles = np.mod(positions[:, 0], 360)
        order = np.argsort(angles)
        if not np.allclose(angles[order], np.arange(360), atol=1e-10):
            raise ValueError("expected every integer azimuth exactly once")
        metadata = {
            "file": path.name, "sha256": sha(path.read_bytes()),
            "source_radius_m": radius,
            "attributes": {k: txt(source.attrs[k]) for k in ["Author", "AuthorContact", "License", "References", "DateModified", "ListenerDescription", "ReceiverDescription", "SourceDescription"]},
            "source_position_type": "spherical",
            "source_position_units": "degree, degree, metre",
            "receiver_position_as_published_m": source["ReceiverPosition"][:].tolist(),
            "data_delay_as_published_samples": source["Data.Delay"][:].tolist(),
            "ir_shape_as_published": list(ir.shape),
        }
        return ir[order], metadata


def ild(ir: np.ndarray) -> float:
    energy = np.sum(np.square(ir), axis=-1)
    return float(10 * np.log10(energy[0] / energy[1]))


def itd(ir: np.ndarray) -> float:
    """Signed xcorr delay R minus L in microseconds; positive = left first.

    Eightfold polyphase interpolation; this is a reproducible engineering metric,
    not the threshold-onset estimator used in the authors' paper.
    """
    left, right = resample_poly(ir, 8, 1, axis=-1)
    corr = correlate(right, left, mode="full", method="fft")
    lag = correlation_lags(len(right), len(left))[np.argmax(corr)]
    return float(lag / (8 * 48000) * 1e6)


def percentiles(values) -> dict:
    values = np.asarray(values, dtype=np.float64)
    return {"median": float(np.median(values)), "p95": float(np.percentile(values, 95)), "max": float(np.max(values))}


def errors(predicted: np.ndarray, truth: np.ndarray) -> dict:
    """Each first-axis item is a direction, then ear and time."""
    relative = np.linalg.norm(predicted - truth, axis=(1, 2)) / np.linalg.norm(truth, axis=(1, 2))
    frequency = np.fft.rfftfreq(4096, 1 / 48000)
    band = (frequency >= 200) & (frequency <= 16000)
    measured = np.abs(np.fft.rfft(truth, n=4096, axis=-1))[..., band]
    estimated = np.abs(np.fft.rfft(predicted, n=4096, axis=-1))[..., band]
    # A per-ear floor relative to the held-out response's strongest bin avoids
    # arbitrary infinite dB errors at spectral zeros. No curve normalization.
    floor = np.max(measured, axis=-1, keepdims=True) * 1e-4
    delta_db = 20 * np.log10(np.maximum(estimated, floor) / np.maximum(measured, floor))
    spectral_rms = np.sqrt(np.mean(delta_db ** 2, axis=-1))
    return {
        "count": int(len(truth)),
        "relative_waveform_l2_error": percentiles(relative),
        "per_ear_log_spectral_rms_error_db_200_16000_hz": percentiles(spectral_rms),
        "absolute_broadband_ild_error_db": percentiles([abs(ild(p) - ild(t)) for p, t in zip(predicted, truth)]),
        "absolute_xcorr_itd_error_us": percentiles([abs(itd(p) - itd(t)) for p, t in zip(predicted, truth)]),
    }


def independent_validation(bank_path: Path, sources: list[Path]) -> dict:
    # Decode the binary using its external wire format, independently reopening
    # each HDF5 source rather than comparing the writer's in-memory arrays.
    content = bank_path.read_bytes()
    magic, rate, rings, angles, taps = struct.unpack_from("<8sIIII", content)
    assert (magic, rate, rings, angles, taps) == (b"KUHRIR01", 48000, 5, 360, 128)
    radii = struct.unpack_from("<5d", content, 24)
    assert radii == tuple(RADII)
    assert len(content) == 24 + 40 + 5 * 360 * 2 * 128 * 4
    bank = np.frombuffer(content, dtype="<f4", offset=64).reshape(5, 360, 2, 128).astype(np.float64)
    original = []
    conversion = []
    cardinals = []
    for r, path in enumerate(sources):
        with h5py.File(path, "r") as source:
            expected = np.empty((360, 2, 128), dtype=np.float64)
            # Position lookup is independent of the preparation's argsort.
            for angle in range(360):
                matches = np.flatnonzero(np.isclose(source["SourcePosition"][:, 0], angle, atol=1e-12))
                assert len(matches) == 1
                expected[angle] = source["Data.IR"][int(matches[0])]
        original.append(expected)
        corrected = expected * GAINS[r]
        assert np.array_equal(bank[r], corrected.astype("<f4").astype(np.float64))
        delta = bank[r] - corrected
        # Separate ear-wide scale fits detect a repeated/missing gain or an ear
        # mismatch. These are diagnostic measurements, not applied calibration.
        observed_gains = [float(np.sum(bank[r, :, e] * expected[:, e]) / np.sum(expected[:, e] ** 2)) for e in [0, 1]]
        assert np.allclose(observed_gains, GAINS[r], rtol=1e-7, atol=1e-12)
        conversion.append({"radius_m": RADII[r], "published_gain": GAINS[r], "observed_left_right_gains": observed_gains,
                           "max_float32_absolute_error": float(np.max(np.abs(delta))),
                           "relative_float32_l2_error": float(np.linalg.norm(delta) / np.linalg.norm(corrected))})
        for angle in [0, 90, 180, 270]:
            cardinals.append({"radius_m": RADII[r], "azimuth_deg": angle, "broadband_ild_l_minus_r_db": ild(bank[r, angle]),
                              "xcorr_itd_r_minus_l_us": itd(bank[r, angle]),
                              "absolute_peak_indices_l_r": np.argmax(np.abs(bank[r, angle]), axis=-1).tolist()})
        assert ild(bank[r, 90]) > 0 and ild(bank[r, 270]) < 0
        assert itd(bank[r, 90]) > 0 and itd(bank[r, 270]) < 0
    original = np.asarray(original)
    corrected = original * np.asarray(GAINS)[:, None, None, None]
    angular = []
    held_out = np.arange(1, 360, 2)
    for r in range(5):
        prediction = (corrected[r, held_out - 1] + corrected[r, (held_out + 1) % 360]) / 2
        angular.append({"radius_m": RADII[r], **errors(prediction, corrected[r, held_out])})
    radial = []
    for r in [1, 2, 3]:
        weight = (np.log(RADII[r]) - np.log(RADII[r - 1])) / (np.log(RADII[r + 1]) - np.log(RADII[r - 1]))
        prediction = (1 - weight) * corrected[r - 1] + weight * corrected[r + 1]
        radial.append({"held_out_radius_m": RADII[r], "bracket_radii_m": [RADII[r - 1], RADII[r + 1]],
                       "log_radius_weight": float(weight), **errors(prediction, corrected[r])})
    return {
        "bank_sha256": sha(content), "extraction_roundtrip_pass": True,
        "roundtrip_definition": "Every coefficient equals float32(original SOFA coefficient * published radius gain); no shift, truncation, ear gain or normalization.",
        "distance_gain_checks": conversion, "cardinal_measurements": cardinals,
        "itd_definition": "xcorr(R,L) maximum after eightfold polyphase interpolation, positive means L earlier; not the paper's threshold-onset ITD",
        "angular_holdout": {"method": "Remove all odd degrees, interpolate their two even neighbors in time domain, compare the held-out measured directions (900 independent targets total). This evaluates a 2-degree gap, not an unmeasured half-degree ground truth.", "rings": angular},
        "radial_holdout": {"method": "Remove one interior measured circle at a time and linearly interpolate coefficients in log(radius) between its neighbors, including the already-corrected distance amplitudes. This quantifies interpolation error, not a pass/fail equivalence claim.", "rings": radial},
        "spectral_metric": "4096-point DFT, 200–16000 Hz inclusive, RMS log-magnitude error, shared floor -80 dB relative to each target ear peak; no level fitting",
        "limits": ["Extraction checks establish implementation correctness, not a physical source model.", "Interpolation targets are held out from interpolation but are from the same measurement session.", "Low frequencies were extended analytically below the authors' 200 Hz crossover.", "No contact, ear deformation, absolute pressure, absolute flight time, or 3Dio transfer validation is possible with these airborne measurements."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path.home() / ".cache" / "ku100-sim" / "4297951")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    paths = acquire(args.source_dir, args.download)
    orientation = verify_orientation(args.source_dir, paths)
    arrays, source_metadata = zip(*(read_original(p, r) for p, r in zip(paths, RADII)))
    corrected = np.asarray(arrays) * np.asarray(GAINS)[:, None, None, None]
    payload = struct.pack("<8sIIII5d", b"KUHRIR01", 48000, 5, 360, 128, *RADII) + corrected.astype("<f4").tobytes(order="C")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "orientation-check.json").write_text(json.dumps(orientation, indent=2, ensure_ascii=False) + "\n")
    bank_path = args.out_dir / "ku100_bank.bin"
    bank_path.write_bytes(payload)
    manifest = {
        "schema": "ku100-bank-provenance-1", "bank": bank_path.name, "sha256": sha(payload), "bytes": len(payload),
        "format": {"magic": "KUHRIR01", "byte_order": "little", "header": "8-byte ASCII magic, four uint32: sample rate/radii/azimuths/taps; float64 radii; float32 [radius][azimuth][ear][tap]", "sample_rate_hz": 48000, "radii_m": RADII, "azimuth_count": 360, "ears": ["left", "right"], "taps": 128},
        "source_record": RECORD, "doi": "10.5281/zenodo.4297951",
        "authors": ["Johannes M. Arend", "Annika Neidhardt", "Christoph Pörschmann"],
        "source_archive_files": [{"file": name, "url": API + name + "/content", "sha256": digest} for name, digest in FILES.items()],
        "source_sofa_files": list(source_metadata),
        "license": {"embedded_source_notice": "CC 3.0 BY-SA", "preserved_derivative_license": "CC-BY-SA-3.0", "url": "https://creativecommons.org/licenses/by-sa/3.0/", "record_metadata_license": "CC-BY-4.0", "conflict": "Record metadata and embedded SOFA notices differ. The derivative retains source-file attribution/share-alike; no relicensing claim is made."},
        "transformation": {"gain_factors_applied_once_to_both_ears": GAINS, "gain_source": "NF_Datasets_Gains_infos.pdf, authors' correction dated 2020-10-09", "operations": ["sort rows by integer source azimuth", "multiply each complete response by its published radius gain", "cast float64 to float32", "serialize native bank"], "normalization": "none", "truncation": "none; all 128 published taps retained", "extra_inverse_distance_gain": False, "additional_eq": False, "delay": "No shifting, alignment or modeled delay applied in this bank; SOFA Data.Delay is zero."},
        "coordinates": {"azimuth_degrees": "0 front, 90 left, 180 rear, 270 right; horizontal only; listener frame", "radius_origin": "center of dummy head, not a pinna/contact gap", "source_channel_order_retained": [0, 1], "receiver_position_caveat": "Published ReceiverPosition has negative y for channel 0, positive y for channel 1; this is inconsistent with customary SOFA positive-y-left labeling. Raw values are preserved in provenance. Named MIRO left/right responses are independently cross-checked in data/orientation-check.json."},
        "calibration": "Relative measured airborne transfer with authors' restored distance levels. No absolute Pa-to-digital calibration or contact transfer is established.",
        "measurement_limits": ["200 Hz adaptive low-frequency extension is analytic postprocessing", "possible head–loudspeaker reflection at 0.25 m", "not elevation-dependent; spherical data were not included", "not a calibration of 3Dio, internal-head transmission, silicone deformation or contact pressure"],
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    validation = independent_validation(bank_path, paths)
    (args.out_dir / "validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"bank": str(bank_path), "sha256": sha(payload), "bytes": len(payload), "extraction_roundtrip_pass": validation["extraction_roundtrip_pass"]}, indent=2))


if __name__ == "__main__":
    main()
