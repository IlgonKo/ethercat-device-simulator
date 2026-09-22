#!/usr/bin/env python3
"""Export committed model dependencies for an isolated Linux test checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,help='Motion Server repository')
    parser.add_argument('--revision',default='HEAD')
    args=parser.parse_args()
    source=Path(args.source).resolve(strict=True)
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','--verify',args.revision+'^{commit}'],text=True).strip()
    subprocess.run(['git','-C',str(source),'cat-file','-e',revision+':device/virtual_device/od_bridge.py'],check=True)
    folder=Path(__file__).resolve().parents[2]/'build'
    folder.mkdir(exist_ok=True)
    archive=folder/f'model-source-{revision[:12]}.tar'
    subprocess.run(['git','-C',str(source),'archive','--format=tar',f'--output={archive}',revision,
                    'device','configuration','motion_server','ethercat','Reference/cmmt_error_catalog.json'],check=True)
    metadata={'revision':revision,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'scope':'Committed model dependencies only; working-tree changes excluded'}
    archive.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(archive)


if __name__=='__main__':main()
