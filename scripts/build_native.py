#!/usr/bin/env python3
"""Build the dependency-free C++17 renderer with a local compiler."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(*, sanitize: bool = False, output: Path | None = None) -> Path:
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError("Install a C++17 compiler (g++ or clang++) before rendering")
    output = output or ROOT / "build" / ("ku100-native-sanitize" if sanitize else "ku100-native")
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror=return-type"]
    flags += ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"] if sanitize else ["-O3", "-DNDEBUG"]
    sources = [ROOT / "native" / x for x in ("main.cpp", "physics.cpp", "receiver.cpp")]
    missing = [str(p) for p in sources if not p.is_file()]
    if missing:
        raise RuntimeError("Missing native sources: " + ", ".join(missing))
    command = shlex.split(compiler) + flags + [str(p) for p in sources] + ["-o", str(output)]
    subprocess.run(command, check=True)
    identity = {
        "compiler": subprocess.check_output(shlex.split(compiler) + ["--version"], text=True).splitlines()[0],
        "flags": flags,
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((ROOT / "native").glob("*")) if p.suffix in (".cpp", ".hpp")},
        "binary_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "sanitizers": sanitize,
    }
    output.with_suffix(".build.json").write_text(json.dumps(identity, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    print(build(sanitize=args.sanitize, output=args.out))
