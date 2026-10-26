#!/usr/bin/env python3
"""Normalize the project's multiline .env for Docker Compose, without shell eval."""
import json
import os
from pathlib import Path
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from simulator.configuration import read_env, load_environment


def main():
    values = read_env(root / '.env')
    load_environment(values, root)
    destination = root / 'build/compose.env'
    destination.parent.mkdir(exist_ok=True)
    text = ''.join(f'{key}={json.dumps(value, ensure_ascii=False)}\n' for key, value in values.items())
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                     prefix='compose-', delete=False) as f:
        temporary = Path(f.name)
        f.write(text)
    try:
        os.chmod(temporary, 0o600)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination)


if __name__ == '__main__':
    main()
