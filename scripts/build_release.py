#!/usr/bin/env python3
"""Build the explicit pressure-release source hypothesis, separate from legacy contact."""
from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def build():
    output=ROOT/'build/ku100-release';output.parent.mkdir(exist_ok=True)
    compiler=shlex.split(os.environ.get('CXX') or shutil.which('g++') or 'g++')
    flags=['-std=c++17','-O3','-Wall','-Wextra','-Wpedantic']
    subprocess.run(compiler+flags+[str(ROOT/'native/release_main.cpp'),str(ROOT/'native/receiver.cpp'),'-o',str(output)],check=True)
    sources=['native/release.hpp','native/release_main.cpp','native/receiver.hpp','native/receiver.cpp','native/viscous.hpp']
    (output.with_suffix('.build.json')).write_text(json.dumps({'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},'binary_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'compiler':subprocess.check_output(compiler+['--version'],text=True).splitlines()[0],'flags':flags},indent=2)+'\n')
    return output
if __name__=='__main__':print(build())
