"""Append a compressed runtime and a versioned cache manifest to the launcher."""
import hashlib
import shutil
import struct
from pathlib import Path

MAGIC = b'DLPCA02\0'
TRAILER = struct.Struct('<8sQQ64sII')


def package(launcher, archive, output, mode=2):
    launcher, archive, output = map(Path, (launcher, archive, output))
    if mode not in (1, 2):
        raise ValueError('Unsupported runtime mode')
    sha = hashlib.sha256()
    with archive.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(data)
    offset, size = launcher.stat().st_size, archive.stat().st_size
    with output.open('wb') as stream:
        for path in (launcher, archive):
            with path.open('rb') as source:
                shutil.copyfileobj(source, stream)
        stream.write(TRAILER.pack(MAGIC, offset, size, sha.hexdigest().encode('ascii'), mode, 0))
    return output
