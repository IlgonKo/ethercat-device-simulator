import hashlib
from functools import lru_cache
from importlib.resources import files

@lru_cache(maxsize=1)
def source_hash():
    digest = hashlib.sha256()
    for package in ('functional_model', 'device_descriptions'):
        root = files(package)
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix in ('.py', '.json', '.xml'):
                digest.update((package+'/'+path.relative_to(root).as_posix()).encode())
                digest.update(b'\0')
                digest.update(path.read_bytes())
    return digest.hexdigest()
