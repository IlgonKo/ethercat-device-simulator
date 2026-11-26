"""Export the standalone pneumatic prototype; never starts Soft ESC or a bus."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'model_sources/pneumatic_cylinder/double_acting'
MODEL = 'SoftESCDoubleActingCylinder'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare_upstream(work: Path, spec: dict) -> Path:
    archive = ROOT / '.cache/downloads/pneumatic_cylinder/pneumatic-circuits.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.is_file():
        temporary = archive.with_suffix('.part')
        with urllib.request.urlopen(spec['archive_url'], timeout=60) as response:
            with temporary.open('wb') as stream:
                shutil.copyfileobj(response, stream)
        temporary.replace(archive)
    if digest(archive) != spec['archive_sha256']:
        raise RuntimeError(f'Upstream source checksum mismatch: {archive}')
    # Re-extract the verified archive so local changes cannot alter provenance.
    destination = (work / 'upstream').resolve()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if not (destination / entry.filename).resolve().is_relative_to(destination):
                raise RuntimeError('Unsafe source archive member')
        bundle.extractall(destination)
    return destination / f"pneumatic-circuits-openmodelica-{spec['commit']}"


def browser_plain_source(source: str) -> str:
    """Remove UI annotations and keep string literals on a single source line."""
    token = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|\bannotation\s*\(', re.S)
    nested = re.compile(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*|[()]', re.S)
    result = []
    position = 0
    while match := token.search(source, position):
        result.append(source[position:match.start()])
        value = match.group()
        if value.startswith('annotation'):
            level, end = 1, match.end()
            while level:
                part = nested.search(source, end)
                if part is None:
                    raise ValueError('Unclosed Modelica annotation')
                level += (part.group() == '(') - (part.group() == ')')
                end = part.end()
            result.append('annotation()')
            position = end
        else:
            result.append(value.replace('\n', r'\n') if value.startswith('"') else value)
            position = match.end()
    result.append(source[position:])
    return ''.join(result)


def browser_components(source: str, names: list[str]) -> str:
    """Select unchanged component definitions from the pinned upstream source."""
    definitions = []
    for name in names:
        pattern = rf'^  (?:partial )?model {re.escape(name)}\b.*?^  end {re.escape(name)};'
        match = re.search(pattern, source, re.M | re.S)
        if match is None:
            raise ValueError(f'Upstream component not found: {name}')
        definitions.append(match.group())
    return '\n\n'.join(definitions)


def build_browser_source(work: Path, upstream: Path) -> Path:
    """One loadable Modelica source file, not a browser-compatible binary FMU."""
    library = upstream / 'modelica/PneumaticCircuits'
    without_within = lambda source: re.sub(r'^\s*within\s*[^;]*;\s*', '', source, count=1)
    package = without_within((library / 'package.mo').read_text(encoding='utf-8'))
    children = [without_within((library / f'{name}.mo').read_text(encoding='utf-8'))
                for name in ['Interfaces', 'Functions']]
    for name, components in [
        ('Sources', ['PressureSupply', 'Tube']),
        ('Valves', ['Valve32', 'PushButtonValve32', 'Valve52', 'DoublePilotValve52']),
        ('Actuators', ['DoubleActingCylinder']),
    ]:
        source = (library / f'{name}.mo').read_text(encoding='utf-8')
        imports = '\n'.join(re.findall(r'^  import [^;]+;', source, re.M))
        children.append(f'package {name}\n{imports}\n' + browser_components(source, components)
                        + f'\nend {name};')
    marker = 'end PneumaticCircuits;'
    assert package.count(marker) == 1
    package = browser_plain_source(package.replace(marker, '\n\n'.join(children) + '\n' + marker))
    license_text = (upstream / 'LICENSE').read_text(encoding='utf-8')
    wrapper = browser_plain_source(without_within((SOURCE / f'{MODEL}.mo').read_text(encoding='utf-8')))
    demo = without_within((SOURCE / 'SoftESCPneumaticDemo.mo').read_text(encoding='utf-8'))
    output = work / 'web/SoftESCPneumaticDemo.mo'
    output.parent.mkdir(parents=True, exist_ok=True)
    # Playground Simulator uses the first class declaration as the run target.
    # Put the runnable scenario before the helper model and library package.
    cylinder_source = (wrapper + '\n'
                       + '/*\nUpstream PneumaticCircuits license:\n' + license_text + '\n*/\n'
                       + package)
    output.write_text(demo + '\n' + cylinder_source, encoding='utf-8')
    # Export the externally commanded cylinder, without the self-running demo.
    export_source = output.with_name(f'{MODEL}.mo')
    export_source.write_text(cylinder_source, encoding='utf-8')
    print(f'Browser source bundle: {output}', flush=True)
    print(f'Browser FMU export source: {export_source}', flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--omc', type=Path, help='Full path to OpenModelica bin/omc.exe')
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'build/pneumatic-fmu-windows')
    parser.add_argument('--output', type=Path, default=ROOT / 'model_artifacts/SoftESCDoubleActingCylinder-win64.fmu')
    parser.add_argument('--browser-only', action='store_true',
                        help='Generate standalone Playground sources on any OS; no compiler needed')
    args = parser.parse_args()
    if args.browser_only:
        spec = json.loads((SOURCE / 'upstream.json').read_text(encoding='utf-8'))
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=True)
        build_browser_source(work, prepare_upstream(work, spec))
        return
    if sys.platform != 'win32':
        parser.error('This prototype build command targets Windows x64.')
    found = args.omc or shutil.which('omc')
    if not found:
        parser.error('Install OpenModelica 1.27.1 or supply --omc <path-to-omc.exe>.')
    omc = Path(found).resolve(strict=True)
    installation = omc.parent.parent
    env = os.environ.copy()
    env['OPENMODELICAHOME'] = str(installation)
    # Portable official distributions need the same tools as an installed OMC.
    tool_dirs = [omc.parent, installation / 'tools/msys/ucrt64/bin',
                 installation / 'tools/msys/mingw64/bin', installation / 'tools/msys/usr/bin']
    env['PATH'] = os.pathsep.join(str(p) for p in tool_dirs if p.is_dir()) + os.pathsep + env['PATH']
    version = subprocess.check_output([str(omc), '--version'], env=env, text=True).strip()
    print(version, flush=True)
    spec = json.loads((SOURCE / 'upstream.json').read_text(encoding='utf-8'))
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    upstream = prepare_upstream(work, spec)
    build_browser_source(work, upstream)
    compile_dir = work / 'compile'
    compile_dir.mkdir(exist_ok=True)
    generated = compile_dir / f'{MODEL}.fmu'
    # A failed compilation must never publish a previous successful artifact.
    generated.unlink(missing_ok=True)
    mos = compile_dir / 'export.mos'
    quote = lambda path: json.dumps(path.as_posix())
    mos.write_text('\n'.join([
        f'loadFile({quote(upstream / spec["package"])});',
        'getErrorString();',
        f'loadFile({quote(SOURCE / (MODEL + ".mo"))});',
        'getErrorString();',
        f'checkModel({MODEL});',
        'getErrorString();',
        'setCommandLineOptions("--fmiFlags=s:cvode --fmuRuntimeDepends=modelica");',
        f'buildModelFMU({MODEL}, version="2.0", fmuType="cs");',
        'getErrorString();',
    ]) + '\n', encoding='utf-8')
    result = subprocess.run([str(omc), str(mos)], cwd=compile_dir, env=env,
                            capture_output=True, text=True, errors='replace', timeout=900)
    log = result.stdout + result.stderr
    (work / 'build.log').write_text(log, encoding='utf-8')
    if result.returncode or not generated.is_file():
        print(log)
        raise RuntimeError(f'FMU export failed. See {work / "build.log"}')
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    shutil.copyfile(generated, temporary)
    with zipfile.ZipFile(temporary, 'a', compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(upstream / 'LICENSE', 'documentation/PneumaticCircuits-LICENSE.txt')
        bundle.write(SOURCE / 'upstream.json', 'documentation/upstream.json')
        bundle.write(SOURCE / (MODEL + '.mo'), f'documentation/{MODEL}.mo')
    with zipfile.ZipFile(temporary) as bundle:
        if f'binaries/win64/{MODEL}.dll' not in bundle.namelist():
            raise RuntimeError('Expected Windows x64 binary is missing')
        flags = json.loads(bundle.read(f'resources/{MODEL}_flags.json'))
        if flags.get('s') != 'cvode':
            raise RuntimeError('CVODE was not selected')
    temporary.replace(output)
    provenance = {**spec, 'compiler': version, 'platform': 'win64',
                  'wrapper_sha256': digest(SOURCE / (MODEL + '.mo')),
                  'fmu_sha256': digest(output)}
    output.with_suffix('.provenance.json').write_text(
        json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(f'Built {output}\nSHA256 {provenance["fmu_sha256"]}', flush=True)


if __name__ == '__main__':
    main()
