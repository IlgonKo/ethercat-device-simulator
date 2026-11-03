#!/usr/bin/env python3
# Prepare hash-locked Docker build inputs; never compile on the host.
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[2]

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--images',action='store_true',help='Verify Docker base/builder digests and prepare offline build tags')
 p.add_argument('--download',action='store_true',help='Allow network downloads of missing inputs')
 p.add_argument('--wheels',type=Path,help='Copy matching wheels from an existing directory')
 args=p.parse_args()
 lock=json.loads((ROOT/'docker/dependency-inputs.json').read_text())
 inputs=ROOT/'docker/inputs';inputs.mkdir(exist_ok=True)
 items=lock['native_sources']+[dict(file='CopleyDriveSim-source.fmu',url=lock['source_fmu_url'],sha256=lock['source_fmu_sha256'])]
 for item in items:
  path=inputs/item['file']
  if not path.exists() and args.download:
   raw=urllib.request.urlopen(item['url'],timeout=120).read()
   if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Downloaded checksum mismatch: '+item['file'])
   path.write_bytes(raw)
  if not path.exists():raise FileNotFoundError(f'{path}: supply offline inputs or use --download')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Checksum mismatch: '+item['file'])
 wheels=ROOT/'docker/wheels';wheels.mkdir(exist_ok=True)
 required=set(re.findall(r'--hash=sha256:([a-f0-9]{64})',(ROOT/'docker/requirements-fmi.txt').read_text()))
 if args.wheels:
  for f in args.wheels.glob('*.whl'):
   if hashlib.sha256(f.read_bytes()).hexdigest() in required and f.resolve()!= (wheels/f.name).resolve():shutil.copy2(f,wheels/f.name)
 present={hashlib.sha256(f.read_bytes()).hexdigest() for f in wheels.glob('*.whl')}
 if not required<=present and args.download:
  subprocess.run([sys.executable,'-m','pip','download','--only-binary=:all:','--platform','manylinux2014_x86_64','--python-version','312','--implementation','cp','--abi','cp312','-r',str(ROOT/'docker/requirements-fmi.txt'),'-d',str(wheels)],check=True)
  present={hashlib.sha256(f.read_bytes()).hexdigest() for f in wheels.glob('*.whl')}
 if not required<=present:raise ValueError('Missing locked FMI wheels; supply --wheels or use --download')
 if args.images:
  for key,role in [('base_image','runtime'),('builder_image','builder')]:
   reference=lock[key]
   metadata=json.loads(subprocess.check_output(['docker','image','inspect',reference],text=True))[0]
   expected=reference.split('@')[1]
   if metadata['Id']!=expected and reference not in metadata.get('RepoDigests',[]):
    raise ValueError('Image digest mismatch: '+reference)
   tag='python:simulator-'+role+'-'+expected.split(':')[1][:12]
   subprocess.run(['docker','tag',reference,tag],check=True)
 print('Docker build inputs verified')

if __name__=='__main__':main()
