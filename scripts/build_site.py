#!/usr/bin/env python3
"""Package only the static viewer and validated, generated example bundles.

The source tree is never modified. This is an explicit publication allowlist,
not a copy of the repository or of arbitrary files beside the examples.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = ("index.html", "styles.css", "app.js", "core.js", "view3d.js")
MAX_APP_BYTES = 2 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_SITE_BYTES = 80 * 1024 * 1024
MAX_EXAMPLES = 16
SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
BUNDLE_NAME = re.compile(r"[a-z][a-z0-9-]{0,63}\.ku100\.json\Z")


def _read_file(path: Path, limit: int) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Expected a regular file, not a link or directory: {path}")
    if info.st_size > limit:
        raise ValueError(f"File exceeds {limit} byte publication limit: {path}")
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError(f"File grew past its publication limit: {path}")
    return data


def _json(data: bytes, label: str) -> dict:
    def constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value in {label}: {value}")

    def real(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            constant(value)
        return number

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(data, parse_constant=constant, parse_float=real,
                           object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {label}")
    return value


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _validate_audio(audio: object, sample_rate: int, duration: float, label: str) -> None:
    if not isinstance(audio, dict) or set(audio) != {"mime", "base64", "sha256", "channels"}:
        raise ValueError(f"Invalid embedded audio fields in {label}")
    if audio["mime"] != "audio/wav" or not isinstance(audio["base64"], str):
        raise ValueError(f"Expected an embedded audio/wav in {label}")
    try:
        raw = base64.b64decode(audio["base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Invalid audio base64 in {label}") from exc
    if type(audio["channels"]) is not int or audio["channels"] != 2:
        raise ValueError(f"Expected declared stereo audio in {label}")
    if not isinstance(audio["sha256"], str) or audio["sha256"] != hashlib.sha256(raw).hexdigest():
        raise ValueError(f"Embedded audio SHA-256 mismatch in {label}")
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError(f"Embedded audio is not RIFF WAVE in {label}")
    if struct.unpack_from("<I", raw, 4)[0] + 8 != len(raw):
        raise ValueError(f"Inconsistent RIFF size in {label}")
    position, fmt, payload = 12, None, None
    while position < len(raw):
        if position + 8 > len(raw):
            raise ValueError(f"Truncated WAVE chunk in {label}")
        key, size = struct.unpack_from("<4sI", raw, position)
        position += 8
        end = position + size
        if end > len(raw):
            raise ValueError(f"Truncated WAVE data in {label}")
        if key == b"fmt ":
            if fmt is not None or size < 16:
                raise ValueError(f"Invalid WAVE format chunk in {label}")
            fmt = struct.unpack_from("<HHIIHH", raw, position)
        elif key == b"data":
            if payload is not None:
                raise ValueError(f"Duplicate WAVE data chunk in {label}")
            payload = memoryview(raw)[position:end]
        elif key != b"fact":
            # Generated examples need no recordings' embedded metadata.
            raise ValueError(f"Unexpected WAVE metadata chunk in {label}")
        position = end + (size & 1)
    if position != len(raw) or fmt is None or payload is None:
        raise ValueError(f"Incomplete WAVE audio in {label}")
    if fmt != (3, 2, sample_rate, sample_rate * 8, 8, 32) or len(payload) % 8:
        raise ValueError(f"Expected stereo Float32 WAVE at the declared sample rate in {label}")
    frames = len(payload) // 8
    if frames == 0 or abs(frames / sample_rate - duration) > 1 / sample_rate:
        raise ValueError(f"Audio duration does not match the bundle in {label}")
    if any(not math.isfinite(value[0]) for value in struct.iter_unpack("<f", payload)):
        raise ValueError(f"Non-finite audio samples in {label}")


def _validate_bundle(data: bytes, label: str) -> None:
    bundle = _json(data, label)
    expected = {"version", "scene", "audio", "sample_rate_hz", "duration_s",
                "metrics", "trace", "geometry", "provenance"}
    if set(bundle) != expected or bundle["version"] != "ku100-render/1":
        raise ValueError(f"Unknown or incomplete render bundle schema in {label}")
    sample_rate, duration = bundle["sample_rate_hz"], bundle["duration_s"]
    if type(sample_rate) is not int or not 8000 <= sample_rate <= 192000:
        raise ValueError(f"Invalid sample rate in {label}")
    if not _number(duration) or not 0 < duration <= 30:
        raise ValueError(f"Example duration must be finite and at most 30 seconds in {label}")
    for field in ("scene", "metrics", "geometry", "provenance"):
        if not isinstance(bundle[field], dict) or not bundle[field]:
            raise ValueError(f"Missing {field} object in {label}")
    trace = bundle["trace"]
    if not isinstance(trace, dict) or set(trace) != {"columns", "rows"}:
        raise ValueError(f"Invalid trace schema in {label}")
    columns, rows = trace["columns"], trace["rows"]
    if (not isinstance(columns, list) or not 1 <= len(columns) <= 64
            or any(not isinstance(column, str) or not 1 <= len(column) <= 96 for column in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError(f"Invalid trace columns in {label}")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100000:
        raise ValueError(f"Invalid trace row count in {label}")
    if any(not isinstance(row, list) or len(row) != len(columns)
           or any(not _number(value) for value in row) for row in rows):
        raise ValueError(f"Non-finite or inconsistent trace dimensions in {label}")
    _validate_audio(bundle["audio"], sample_rate, duration, label)


def _check_output(output: Path, source: Path) -> None:
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError("Output path must not contain symbolic links")
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Output must be separate from the web source tree")
    if output.exists():
        if not output.is_dir():
            raise ValueError("Output already exists and is not a directory")
        # Only replace a directory that already has the generated site's shape.
        # An accidental --output pointing at source files must not delete them.
        for path in output.rglob("*"):
            relative = path.relative_to(output)
            if path.is_symlink():
                raise ValueError(f"Refusing to replace a linked output: {relative}")
            if path.is_dir() and relative.as_posix() == "examples":
                continue
            if path.is_file() and (relative.as_posix() in APP_FILES
                    or relative.as_posix() == "examples/index.json"
                    or (relative.parent.as_posix() == "examples" and BUNDLE_NAME.fullmatch(relative.name))):
                continue
            raise ValueError(f"Refusing to replace an output containing unexpected content: {relative}")


def build_site(source: Path = ROOT / "web", output: Path = ROOT / "dist") -> dict:
    source, output = source.absolute(), output.absolute()
    if source.is_symlink() or any(parent.is_symlink() for parent in source.parents) or not source.is_dir():
        raise ValueError("Web source must be a real directory")
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError("Output path must not contain symbolic links")
    # Normalize '..' before comparing directory ownership, but reject links
    # before resolving so resolution cannot silently authorize a linked path.
    source, output = source.resolve(), output.resolve()
    examples_dir = source / "examples"
    if examples_dir.is_symlink() or not examples_dir.is_dir():
        raise ValueError("Generate web/examples before building the site")
    _check_output(output, source)
    files = {name: _read_file(source / name, MAX_APP_BYTES) for name in APP_FILES}
    manifest_bytes = _read_file(examples_dir / "index.json", MAX_MANIFEST_BYTES)
    manifest = _json(manifest_bytes, "examples/index.json")
    examples = manifest.get("examples")
    if (set(manifest) != {"version", "examples"} or type(manifest["version"]) is not int
            or manifest["version"] != 1 or not isinstance(examples, list)
            or not 1 <= len(examples) <= MAX_EXAMPLES):
        raise ValueError("Expected examples manifest version 1 with 1–16 examples")
    ids, names = set(), set()
    for entry in examples:
        if not isinstance(entry, dict) or set(entry) != {"id", "title", "description", "path"}:
            raise ValueError("Unknown examples manifest fields")
        identifier, name = entry["id"], entry["path"]
        if not isinstance(identifier, str) or not SLUG.fullmatch(identifier) or identifier in ids:
            raise ValueError("Example IDs must be unique lowercase slugs")
        if not isinstance(name, str) or not BUNDLE_NAME.fullmatch(name) or name in names:
            raise ValueError("Example paths must be unique local .ku100.json basenames")
        if any(not isinstance(entry[field], str) or not 1 <= len(entry[field]) <= (120 if field == "title" else 1000)
               for field in ("title", "description")):
            raise ValueError("Each example needs a short title and description")
        ids.add(identifier)
        names.add(name)
        data = _read_file(examples_dir / name, MAX_BUNDLE_BYTES)
        _validate_bundle(data, name)
        files[f"examples/{name}"] = data
    unknown = {entry.name for entry in examples_dir.iterdir()} - names - {"index.json"}
    if unknown:
        raise ValueError(f"Unlisted files in generated examples directory: {sorted(unknown)}")
    files["examples/index.json"] = manifest_bytes
    total = sum(map(len, files.values()))
    if total > MAX_SITE_BYTES:
        raise ValueError("Site exceeds the 80 MiB publication limit")

    # Validate every input before writing or replacing the previous output.
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        for name, data in files.items():
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"output": str(output), "files": sorted(files), "examples": len(examples), "bytes": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        print(json.dumps(build_site(output=args.output), indent=2))
    except (OSError, ValueError, OverflowError) as exc:
        parser.exit(1, f"Site packaging failed: {exc}\n")
