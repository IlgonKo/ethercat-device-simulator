#!/usr/bin/env python3
# Offline Linux x86_64 package. Never starts containers or opens a NIC.
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

BASE = 'python@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9'
SOURCE_FMU_SHA = 'e6456f4787b61b209f0e718c62ee3d570560ce975b7aacf733da6d4f21994b4d'
ROOT = Path(__file__).resolve().parents[2]


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def output(args, **kwargs):
    return subprocess.check_output([str(x) for x in args], text=True, **kwargs).strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def verify(folder):
    folder = folder.resolve()
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['schema'] not in (1,2): raise ValueError('Unsupported manifest schema')
    actual = set()
    for path in folder.rglob('*'):
        if path.is_symlink(): raise ValueError(f'Symlink refused: {path}')
        if path.is_file() and path != folder / 'manifest.json':
            actual.add(path.relative_to(folder).as_posix())
    if actual != set(manifest['sha256']): raise ValueError('Bundle file list mismatch')
    for name, expected in manifest['sha256'].items():
        path = folder / name
        if not path.resolve().is_relative_to(folder): raise ValueError('Unsafe bundle path')
        if digest(path) != expected: raise ValueError(f'Hash mismatch: {name}')
    return manifest


def copy_file(source, destination):
    if source.is_symlink() or not source.is_file(): raise ValueError(f'Expected regular file: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_locked_wheels(requirements, sources, destination):
    required = set(re.findall(r'--hash=sha256:([a-f0-9]{64})', requirements.read_text()))
    found = set()
    for folder in sources:
        for wheel in folder.glob('*.whl'):
            h = digest(wheel)
            if h in required:
                copy_file(wheel, destination / wheel.name)
                found.add(h)
    if found != required: raise ValueError(f'Missing {len(required-found)} locked wheels')


def export(args):
    destination = args.destination.resolve()
    if destination.exists(): raise ValueError('Destination must not exist')
    root = ROOT
    kickcat = root / 'third_party/KickCAT'
    locked=json.loads((root/'docker/dependency-inputs.json').read_text())
    if output(['git', '-C', kickcat, 'status', '--porcelain', '--untracked-files=no']):
        raise ValueError('KickCAT must have no tracked changes')
    image = json.loads(output(['docker', 'image', 'inspect', args.image]))[0]
    if image['Architecture'] != 'amd64': raise ValueError('Expected amd64 image')
    destination.mkdir(parents=True)
    # Tracked source plus this delivery tool/lock; exclude unrelated untracked files.
    tracked = output(['git', '-C', root, 'ls-files', '-z']).split('\0')
    extras = ['docker/dependency-inputs.json', 'docker/requirements-build.txt',
              'docker/build-native.py', 'docker/inputs/.gitkeep', 'compose.external-fmu.yaml',
              'scripts/docker/prepare-inputs.py', 'scripts/deployment/offline.py',
              'scripts/deployment/README.md', 'tests/unit/test_offline_bundle.py',
              'Doc/Validation/RF-012/offline-deployment-20261103.md',
              'Doc/Validation/RF-012/multistage-build-20261103.md']
    for name in sorted(set(tracked + extras)):
        if not name or name == 'third_party/KickCAT': continue
        copy_file(root / name, destination / 'source' / name)
    run(['git', '-C', root, 'bundle', 'create', destination / 'repository.bundle', 'HEAD'])
    run(['git', '-C', kickcat, 'bundle', 'create', destination / 'kickcat.bundle', 'HEAD'])
    copy_locked_wheels(root/'docker/requirements-fmi.txt', args.wheels, destination/'wheels/fmi')
    for item in locked['native_sources']+[dict(file='CopleyDriveSim-source.fmu',sha256=locked['source_fmu_sha256'])]+locked.get('binary_fmus',[]):
        source=args.inputs/item['file']
        if digest(source)!=item['sha256']:raise ValueError('Build input checksum mismatch: '+item['file'])
        copy_file(source,destination/'inputs'/item['file'])
    run(['docker', 'save', '-o', destination/'runtime-image.tar', args.image])
    # Save named references: digest-only archives can lose repository association on a fresh daemon.
    base_tag='python:simulator-runtime-'+BASE.split(':')[-1][:12]
    run(['docker','tag',BASE,base_tag])
    run(['docker', 'save', '-o', destination/'base-image.tar', base_tag])
    builder_tag='python:simulator-builder-'+locked['builder_image'].split(':')[-1][:12]
    run(['docker','tag',locked['builder_image'],builder_tag])
    run(['docker', 'save', '-o', destination/'builder-image.tar', builder_tag])
    manifest = dict(schema=2, platform='linux/amd64', python='3.12',
        source_commit=output(['git','-C',root,'rev-parse','HEAD']),
        source_snapshot='tracked working tree plus deployment tool and build lock; hashes authoritative',
        source_changes=output(['git','-C',root,'status','--short']),
        kickcat_commit=output(['git','-C',kickcat,'rev-parse','HEAD']),
        image_id=image['Id'], image_tag=args.image, base=BASE,
        builder=locked['builder_image'],
        build_host=dict(machine=platform.machine(), docker=output(['docker','version','--format','{{.Server.Version}}'])),
        native_sources=locked['native_sources'],
        sha256={p.relative_to(destination).as_posix():digest(p)
                for p in sorted(destination.rglob('*')) if p.is_file()})
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    verify(destination)
    print(f'Exported and verified: {destination}')


def restore_source(folder, destination, manifest):
    if destination.exists(): raise ValueError('Work directory must not exist')
    run(['git','clone',folder/'repository.bundle',destination])
    run(['git','-C',destination,'checkout','--detach',manifest['source_commit']])
    kickcat=destination/'third_party/KickCAT'
    run(['git','clone',folder/'kickcat.bundle',kickcat])
    run(['git','-C',kickcat,'checkout','--detach',manifest['kickcat_commit']])
    shutil.copytree(folder/'source',destination,dirs_exist_ok=True)


def restore(args):
    folder=args.bundle.resolve();manifest=verify(folder)
    destination=args.work.resolve()
    restore_source(folder,destination,manifest)
    # These are inputs only; do not create .env or copy production state.
    if (folder/'model_artifacts').exists():
        shutil.copytree(folder/'model_artifacts',destination/'model_artifacts',dirs_exist_ok=True)
    print(f'Source restored: {destination}')


def rebuild(args):
    folder=args.bundle.resolve();manifest=verify(folder)
    if manifest['schema']!=2:raise ValueError('Use a schema 2 multi-stage build bundle')
    destination=args.work.resolve()
    restore_source(folder,destination,manifest)
    shutil.copytree(folder/'wheels/fmi',destination/'docker/wheels',dirs_exist_ok=True)
    shutil.copytree(folder/'inputs',destination/'docker/inputs',dirs_exist_ok=True)
    for name in ('base-image.tar','builder-image.tar'):
        run(['docker','load','-i',folder/name])
    run([sys.executable,'scripts/docker/prepare-inputs.py','--images'],cwd=destination)
    base_tag='python:simulator-runtime-'+manifest['base'].split(':')[-1][:12]
    builder_tag='python:simulator-builder-'+manifest['builder'].split(':')[-1][:12]
    run(['docker','build','--network','none','--pull=false','--build-arg',f'BASE_IMAGE={base_tag}',
         '--build-arg',f'BUILDER_IMAGE={builder_tag}',
         '-f','docker/Dockerfile','-t',args.image,'.'],cwd=destination)
    print(f'Rebuilt {args.image} entirely in Docker; no container was started')


def main():
    parser=argparse.ArgumentParser(description='Offline bundle: verify, restore or rebuild without starting services')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('destination',type=Path)
    p.add_argument('--image',required=True)
    p.add_argument('--wheels',type=Path,nargs='+',required=True)
    p.add_argument('--inputs',type=Path,default=ROOT/'docker/inputs')
    for command in ('verify','restore','rebuild','load-image'):
        p=sub.add_parser(command);p.add_argument('bundle',type=Path)
        if command in ('restore','rebuild'):p.add_argument('--work',type=Path,required=True)
        if command=='rebuild':p.add_argument('--image',required=True)
    args=parser.parse_args()
    if platform.system()!='Linux': parser.error('Run on Linux')
    if args.command in ('export','load-image','rebuild') and platform.machine()!='x86_64':
        parser.error('This bundle targets Linux x86_64')
    if args.command=='export':export(args)
    elif args.command=='restore':restore(args)
    elif args.command=='rebuild':rebuild(args)
    else:
        m=verify(args.bundle)
        if args.command=='load-image':
            run(['docker','load','-i',args.bundle/'runtime-image.tar'])
            if output(['docker','image','inspect','--format','{{.Id}}',m['image_tag']])!=m['image_id']:
                raise ValueError('Loaded image ID mismatch')
        print('Bundle verification passed')


if __name__=='__main__':
    main()
