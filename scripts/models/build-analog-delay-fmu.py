#!/usr/bin/env python3
"""Reproducible Linux x86-64 FMI 3.0 scalar pure-delay artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'model_sources/signal_processing/delay'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'model_artifacts/SoftESCAnalogDelay-linux.fmu');a=p.parse_args()
    if platform.system()!='Linux' or platform.machine()!='x86_64':p.error('Linux x86-64 build required')
    import fmpy
    headers=Path(fmpy.__file__).parent/'c-code'
    code=(SOURCE/'analog_delay.c').read_text()
    signatures={name:(ret,args) for ret,name,args in re.findall(r'typedef\s+([\w *]+?)\s+(fmi3\w+)TYPE\s*\((.*?)\);',(headers/'fmi3FunctionTypes.h').read_text(),re.S)}
    exports=re.findall(r'FMI3_Export\s+\w+TYPE\s+(fmi3\w+)\s*;',(headers/'fmi3Functions.h').read_text())
    implemented=set(re.findall(r'\b(fmi3[A-Z]\w+)\s*\(',code))
    stubs=['#include "fmi3Functions.h"']
    for name in exports:
        if name in implemented:continue
        ret,args=signatures[name];ret=' '.join(ret.split())
        body='return fmi3Error;' if ret=='fmi3Status' else 'return NULL;' if ret=='fmi3Instance' else '' if ret=='void' else None
        if body is None:raise ValueError('Unexpected FMI function type: '+name)
        stubs.append(f'{ret} {name}({args}) {{ {body} }}')
    if not exports or not implemented<=set(exports):raise ValueError('FMI header/export mismatch')
    with tempfile.TemporaryDirectory(prefix='delay-fmu-build-') as directory:
        stage=Path(directory);sources=stage/'sources';sources.mkdir()
        (sources/'analog_delay.c').write_text(code);(sources/'unsupported.c').write_text('\n'.join(stubs))
        for name in ['fmi3Functions.h','fmi3FunctionTypes.h','fmi3PlatformTypes.h']:(sources/name).write_bytes((headers/name).read_bytes())
        (sources/'buildDescription.xml').write_text('<fmiBuildDescription fmiVersion="3.0"><BuildConfiguration modelIdentifier="SoftESCAnalogDelay"><SourceFileSet language="C99"><SourceFile name="analog_delay.c"/><SourceFile name="unsupported.c"/></SourceFileSet></BuildConfiguration></fmiBuildDescription>')
        (stage/'modelDescription.xml').write_bytes((SOURCE/'modelDescription.xml').read_bytes())
        (stage/'documentation').mkdir();(stage/'documentation/README.md').write_bytes((SOURCE/'README.md').read_bytes())
        binary=stage/'binaries/x86_64-linux/SoftESCAnalogDelay.so';binary.parent.mkdir(parents=True)
        subprocess.run(['cc','-std=c99','-shared','-fPIC','-O2','-Wl,--build-id=none','-I'+str(sources),str(sources/'analog_delay.c'),str(sources/'unsupported.c'),'-lm','-o',str(binary)],check=True)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=a.output.with_suffix('.tmp')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            for file in sorted(stage.rglob('*')):
                if file.is_file():
                    info=zipfile.ZipInfo(file.relative_to(stage).as_posix(),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
                    z.writestr(info,file.read_bytes())
        from fmpy.validation import validate_fmu
        errors=validate_fmu(str(temporary))
        if errors:raise ValueError(errors)
        temporary.replace(a.output)
    report=dict(platform='x86_64-linux',fmi='3.0',fmpy=fmpy.__version__,
                source_sha256=hashlib.sha256(code.encode()).hexdigest(),artifact_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())
    a.output.with_suffix('.provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
