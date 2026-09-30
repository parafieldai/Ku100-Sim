#!/usr/bin/env python3
"""Add only validated object auditions to the previous generated-only site."""
from pathlib import Path
import argparse,json,shutil,tempfile
from build_site import ROOT,_read_file,_json,MAX_SITE_BYTES
from package_long_site import package as package_previous
from object_publication import collect


def package(output):
    source=ROOT/'web';output=Path(output).absolute()
    if output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Linked output')
    output=output.resolve()
    if output==source or source in output.parents or output in source.parents:raise ValueError('Output overlaps source')
    added=collect(source,_read_file,_json)
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.object-site-',dir=output.parent))
    try:
        previous=package_previous(stage)
        total=previous['bytes']+sum(map(len,added.values()))
        if total>MAX_SITE_BYTES:raise ValueError('Original 80 MiB site budget exceeded')
        for name,data in added.items():
            p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        names=set(previous['files'])|set(added)
        directories={parent.as_posix() for name in names for parent in Path(name).parents if parent.as_posix()!='.'}
        if output.exists():
            if not output.is_dir():raise ValueError('Output is not a directory')
            for p in output.rglob('*'):
                rel=p.relative_to(output).as_posix()
                if p.is_symlink() or not ((p.is_file() and rel in names) or (p.is_dir() and rel in directories)):
                    raise ValueError('Refusing to replace unknown output: '+rel)
            shutil.rmtree(output)
        stage.replace(output)
        return {'output':str(output),'bytes':total,'files':sorted(names),'reference_recordings_published':False}
    finally:
        if stage.exists():shutil.rmtree(stage)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'dist');a=p.parse_args();print(json.dumps(package(a.out),indent=2))
