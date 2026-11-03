import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

root=Path('/workspace')
lock=json.loads((root/'docker/dependency-inputs.json').read_text())
options={
 'argparse':['-DARGPARSE_BUILD_TESTS=OFF','-DARGPARSE_INSTALL=ON'],
 'json':['-DJSON_BuildTests=OFF','-DJSON_Install=ON'],
 'tinyxml2':['-Dtinyxml2_BUILD_TESTING=OFF'],
}
for item in lock['native_sources']:
 archive=root/'docker/inputs'/item['file']
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=item['sha256']:
  raise ValueError(f'Checksum mismatch: {archive}')
 destination=Path('/tmp/native-sources')/item['file'].removesuffix('.tar.gz')
 destination.mkdir(parents=True)
 with tarfile.open(archive) as t:t.extractall(destination,filter='data')
 source=next(destination.iterdir());build=destination/'build'
 key=item['file'].split('-')[0]
 subprocess.run(['cmake','-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release',
  '-DCMAKE_INSTALL_PREFIX=/opt/deps','-DBUILD_SHARED_LIBS=OFF',*options[key]],check=True)
 subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
 subprocess.run(['cmake','--install',str(build)],check=True)
