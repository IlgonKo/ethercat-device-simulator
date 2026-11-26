#!/usr/bin/env python3
"""Copy explicitly pinned binary FMUs intact into runtime artifacts."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
def main():
    lock=json.loads((ROOT/'docker/dependency-inputs.json').read_text())
    target=ROOT/'model_artifacts';target.mkdir(exist_ok=True)
    for item in lock['binary_fmus']:
        source=ROOT/'docker/inputs'/item['file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Binary FMU checksum mismatch: '+item['file'])
        shutil.copyfile(source,target/item['file'])
        (target/Path(item['file']).with_suffix('.provenance.json')).write_text(json.dumps(item,indent=2)+'\n')
        print('Verified and packaged '+item['file'])
if __name__=='__main__':main()
