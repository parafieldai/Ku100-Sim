#!/usr/bin/env python3
"""Rebuild the original allowlisted site and append a validated long comparison.

This separate packager keeps the original viewer/preview builder unchanged.
Existing output is replaced only when it contains generated site paths.
"""
from pathlib import Path
import argparse,json,shutil,tempfile
from build_site import ROOT,build_site,_read_file,_json,_validate_audio,MAX_SITE_BYTES
from long_publication import collect

def package(output):
    source=ROOT/'web';output=Path(output).absolute()
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Linked output')
    output=output.resolve()
    if output==source or source in output.parents or output in source.parents:raise ValueError('Output overlaps source')
    added=collect(source,_read_file,_json,_validate_audio)
    if not added:raise ValueError('Long comparison must be generated first')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.long-site-',dir=output.parent))
    try:
        result=build_site(output=stage)
        total=result['bytes']+sum(map(len,added.values()))
        if total>MAX_SITE_BYTES:raise ValueError('Site exceeds its original 80 MiB limit')
        for name,data in added.items():
            p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        names=set(result['files'])|set(added)
        directories={str(parent) for name in names for parent in Path(name).parents if str(parent)!='.'}
        if output.exists():
            if not output.is_dir():raise ValueError('Output is not a directory')
            for p in output.rglob('*'):
                rel=p.relative_to(output).as_posix()
                if p.is_symlink() or not ((p.is_file() and rel in names) or (p.is_dir() and rel in directories)):
                    raise ValueError('Refusing to replace unknown output content: '+rel)
            shutil.rmtree(output)
        stage.replace(output)
        return {'output':str(output),'bytes':total,'files':sorted(names),'reference_audio_public':False}
    finally:
        if stage.exists():shutil.rmtree(stage)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'dist');a=parser.parse_args()
    print(json.dumps(package(a.out),indent=2))
