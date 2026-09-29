#!/usr/bin/env python3
"""Compare the native KU100 bank with an independent SADIE II D1 session.

Download the author's D1_HRIR_SOFA.zip from Zenodo record 12092466 and pass its
D1_48K_24bit_256tap_FIR_SOFA.sofa with --sadie. No fit changes runtime data.
This reports cross-session disagreement, not a contact-equivalence pass/fail.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import h5py
import numpy as np
from prepare_ku100 import itd, ild, percentiles

ROOT = Path(__file__).resolve().parents[1]
SADIE_HASH = "9af7cb19531e52fb7ae8ec92621e6ab62b1d5fe584b3742be36699a0ddb0ccd4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sadie", type=Path, required=True)
    parser.add_argument("--bank", type=Path, default=ROOT / "data/ku100_bank.bin")
    parser.add_argument("--out", type=Path, default=ROOT / "data/sadie-benchmark.json")
    args = parser.parse_args()
    actual_hash = hashlib.sha256(args.sadie.read_bytes()).hexdigest()
    if actual_hash != SADIE_HASH:
        raise ValueError(f"SADIE source version differs: {actual_hash}")
    blob = args.bank.read_bytes()
    assert struct.unpack_from("<8sIIII", blob) == (b"KUHRIR01", 48000, 5, 360, 128)
    radii = np.array(struct.unpack_from("<5d", blob, 24))
    bank = np.frombuffer(blob, dtype="<f4", offset=64).reshape(5, 360, 2, 128).astype(float)
    w = (np.log(1.2) - np.log(radii[3])) / (np.log(radii[4]) - np.log(radii[3]))
    estimate = (1 - w) * bank[3] + w * bank[4]
    with h5py.File(args.sadie) as source:
        assert source["Data.SamplingRate"][0] == 48000
        pos = source["SourcePosition"][:]
        selected = []
        for angle in range(360):
            matching = np.flatnonzero(np.isclose(pos[:, 0], angle, atol=1e-8) & np.isclose(pos[:, 1], 0, atol=1e-8))
            assert len(matching) == 1
            selected.append(int(matching[0]))
        reference = np.asarray([source["Data.IR"][i] for i in selected])
        assert np.allclose(pos[selected, 2], 1.2)
        provenance = {k: bytes(source.attrs[k]).decode() for k in ["License", "Comment", "History", "References", "DateModified"]}
    frequency = np.fft.rfftfreq(4096, 1 / 48000)
    band = (frequency >= 200) & (frequency <= 16000)
    magnitude = [np.abs(np.fft.rfft(x, n=4096, axis=-1))[..., band] for x in [estimate, reference]]
    # Fixed global floor prevents a deep notch from producing infinite dB.
    floor = max(float(x.max()) for x in magnitude) * 1e-5
    pred_db, ref_db = [20 * np.log10(np.maximum(x, floor)) for x in magnitude]
    raw_difference = pred_db - ref_db
    # One common scalar, shared by both ears and every source direction. No
    # direction-dependent, ear-dependent or frequency-dependent fitting.
    common_gain_db = -float(np.mean(raw_difference))
    spectral_error = np.sqrt(np.mean((raw_difference + common_gain_db) ** 2, axis=-1))
    ild_spectrum_difference = (pred_db[:, 0] - pred_db[:, 1]) - (ref_db[:, 0] - ref_db[:, 1])
    ild_spectral_rms = np.sqrt(np.mean(ild_spectrum_difference ** 2, axis=-1))
    timing_errors = [abs(itd(p) - itd(t)) for p, t in zip(estimate, reference)]
    cardinals = []
    for angle in [0, 90, 180, 270]:
        cardinals.append({"azimuth_deg": angle, "thk_ild_db": ild(estimate[angle]), "sadie_ild_db": ild(reference[angle]),
                          "thk_xcorr_itd_us": itd(estimate[angle]), "sadie_xcorr_itd_us": itd(reference[angle])})
    assert ild(reference[90]) > 0 and ild(reference[270]) < 0
    assert itd(reference[90]) > 0 and itd(reference[270]) < 0
    report = {
        "kind": "independent KU100 session comparison, not an equivalence or contact certification",
        "source_record": "https://zenodo.org/records/12092466", "source_doi": "10.5281/zenodo.12092466",
        "archive_url": "https://zenodo.org/api/records/12092466/files/D1_HRIR_SOFA.zip/content",
        "archive_sha256": "366321fa78f211bacc0ec6bea96701625b196a5db54ec16748b0eab0b9705f75",
        "sofa_file": args.sadie.name, "sofa_sha256": actual_hash, "source_metadata": provenance,
        "bank_sha256": hashlib.sha256(blob).hexdigest(), "sample_rate": 48000, "direction_count": 360,
        "reference_radius_m": 1.2, "native_interpolation": "time-domain coefficient interpolation between1.0/1.5m using log-radius weight", "native_interpolation_weight": float(w),
        "reference_taps": 256, "bank_taps": 128,
        "orientation_sign_checks_pass": True,
        "common_gain_db_applied_to_thk_for_spectral_comparison_only": common_gain_db,
        "spectral_rms_disagreement_db_after_one_common_gain": percentiles(spectral_error),
        "frequency_dependent_ild_rms_disagreement_db": percentiles(ild_spectral_rms),
        "xcorr_itd_absolute_disagreement_us": percentiles(timing_errors),
        "cardinals": cardinals,
        "metric": "4096-point DFT,200–16000Hz,global -100dB magnitude floor; all directions and both ears share one fitted dB offset; ITD is8x-resampled xcorr(R,L) lag",
        "limits": ["The datasets use different source hardware, preamps, equalization, timing and possibly individual KU100 units.", "SADIE metadata explicitly declares low-frequency extension and diffuse-field equalization; this is not raw unprocessed ground truth.", "The THK1.2m response is interpolated, introducing its own error.", "Broadband correlation can select different peaks across spectral/coloration differences.", "No spectral equalizer, independent ear gain or timing shift is fitted; discrepancy is retained.", "No assertion that simulated contact matches measured hardware follows from these numbers."],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in ["direction_count", "orientation_sign_checks_pass", "common_gain_db_applied_to_thk_for_spectral_comparison_only", "spectral_rms_disagreement_db_after_one_common_gain", "frequency_dependent_ild_rms_disagreement_db", "xcorr_itd_absolute_disagreement_us"]}, indent=2))


if __name__ == "__main__":
    main()
