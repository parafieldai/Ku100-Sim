#!/usr/bin/env python3
"""Check current documentation links and archived evidence hashes.

This is a repository-integrity check, not a physical or perceptual validation.
"""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT/'README.md', ROOT/'docs/RESEARCH_INDEX.md',
        ROOT/'docs/IMPLEMENTATION_AUDIT.md', ROOT/'docs/PHYSICS.md']

def main():
    checked=0
    for document in DOCS:
        for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
            url=urlsplit(target)
            if url.scheme or not url.path: continue
            path=(document.parent/unquote(url.path)).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                raise ValueError(f'Unresolved repository link: {document.relative_to(ROOT)} -> {target}')
            checked+=1
    directory=ROOT/'validation/reports/2026-09-29-quality'
    manifest=json.loads((directory/'manifest.json').read_text())
    hashes=0
    for name,record in manifest['files'].items():
        if name=='delivered_markdown_source': continue
        path=directory/name;data=path.read_bytes()
        if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
            raise ValueError('Archived evidence identity mismatch: '+name)
        hashes+=1
    print(json.dumps({'repository_links_checked':checked,'historical_file_hashes_checked':hashes,
                      'passed':True,'meaning':'File/link integrity only; no realism claim'}))
if __name__=='__main__':main()
