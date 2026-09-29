#!/usr/bin/env python3
"""Build static examples by executing the native renderer on tracked scenes.

Only generated bundles and a manifest are copied to web/examples. Recordings,
downloaded data, raw inputs and build artifacts are never published by this step.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from render import ROOT, ensure_binary, render


EXAMPLES = [
    ("stroke-left", "Dry stroke / left", "Fresh physical contact on the generic left plate; the opposite channel is transmitted through the modeled fixture."),
    ("wet-stroke-left", "Viscous film / left", "The same stroke with an idealized Newtonian film. This models viscous force and loss; it is not validated wet ASMR."),
    ("tap-right", "Tap / right", "A single prescribed tool indentation drives the right plate, followed by physical decay."),
    ("airborne-left", "Measured KU100 receiver", "A synthesized vent source through measured horizontal KU100 responses at 0.5 m, 90 degrees. Absolute level is uncalibrated."),
    ("press-left", "Press and release", "A smooth normal engagement without texture sliding; compare its force and chamber pressure against the stroke."),
]


def generate(destination: Path | None = None):
    destination = destination or ROOT / "web" / "examples"
    for candidate in (destination, *destination.parents):
        if candidate.is_symlink():
            raise ValueError("Generated example directory and its ancestors must not be symlinks")
        if candidate == ROOT:
            break
    destination = destination.resolve()
    if destination != (ROOT / "web" / "examples").resolve():
        raise ValueError("Example generation writes only this repository's web/examples directory")
    allowed = {"index.json"} | {identifier + ".ku100.json" for identifier, _, _ in EXAMPLES}
    if destination.exists():
        if not destination.is_dir() or any(p.name not in allowed or not p.is_file() or p.is_symlink()
                                            for p in destination.iterdir()):
            raise ValueError("Refusing to replace unexpected files in generated examples")
    executable, _ = ensure_binary(None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ku100-examples-", dir=ROOT / "build") as temporary:
        work = Path(temporary)
        staged = work / "examples"
        staged.mkdir()
        entries = []
        for identifier, title, description in EXAMPLES:
            result = render(ROOT / "scenes" / (identifier + ".json"), work / identifier, binary=executable)
            filename = identifier + ".ku100.json"
            shutil.copyfile(result["bundle"], staged / filename)
            entries.append({"id": identifier, "title": title, "description": description, "path": filename})
            print(json.dumps({"example": identifier, "frames": result["metrics"]["frames"],
                              "rms_dbfs": result["metrics"]["rms_dbfs"],
                              "samples_above_full_scale": result["metrics"]["samples_above_full_scale"]}), flush=True)
        (staged / "index.json").write_text(json.dumps({"version": 1, "examples": entries}, indent=2) + "\n")
        # Rendering/validation must finish before replacing the generated set.
        backup = work / "previous"
        if destination.exists():
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(generate())
