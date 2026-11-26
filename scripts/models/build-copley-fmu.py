#!/usr/bin/env python3
"""Build the pinned upstream source FMU on Linux x86_64, without MATLAB."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / 'model_sources/motor_controller/copley/upstream.json').read_text())
REVISION = SPEC['revision']
URL = SPEC['source_url']
SOURCE_SHA256 = SPEC['source_sha256']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Previously downloaded source FMU')
    parser.add_argument('--output', type=Path, default=Path('build/fmu/CopleyDriveSim-linux.fmu'))
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        parser.error('This build recipe requires Linux x86_64')
    import fmpy
    raw = args.source.read_bytes() if args.source else urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source FMU checksum mismatch')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='copley-build-') as directory:
        root = Path(directory)
        source = root / 'source.fmu'
        source.write_bytes(raw)
        stage = root / 'stage'
        with zipfile.ZipFile(source) as archive: archive.extractall(stage)
        sources = stage / 'sources'
        binary = stage / 'binaries/x86_64-linux/CopleyDriveSim.so'
        binary.parent.mkdir(parents=True)
        command = ['cc', '-shared', '-fPIC', '-O2', '-DDISABLE_PREFIX',
                   '-I' + str(sources), '-I' + str(Path(fmpy.__file__).parent / 'c-code'),
                   *map(str, sorted(sources.glob('*.c'))), '-lm', '-o', str(binary)]
        subprocess.run(command, check=True)
        with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob('*')):
                if path.is_file(): archive.write(path, path.relative_to(stage))
    report = dict(upstream=URL, revision=REVISION, source_sha256=SOURCE_SHA256,
                  artifact_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  platform='x86_64-linux', fmpy=fmpy.__version__)
    args.output.with_suffix('.provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
