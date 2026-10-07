import hashlib
import tempfile
import unittest
from pathlib import Path
from package_exe import package, TRAILER, MAGIC


class PackagingTests(unittest.TestCase):
    def test_payload_offset_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher, archive, output = root / 'launcher', root / 'runtime.zip', root / 'app.exe'
            launcher.write_bytes(b'MZfixture')
            archive.write_bytes(b'compressed runtime fixture')
            package(launcher, archive, output)
            blob = output.read_bytes()
            magic, offset, size, hash_value, mode, _ = TRAILER.unpack(blob[-TRAILER.size:])
            self.assertEqual(magic, MAGIC)
            self.assertEqual(blob[offset:offset + size], archive.read_bytes())
            self.assertEqual(offset + size, len(blob) - TRAILER.size)
            self.assertEqual(hash_value.decode(), hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(mode, 2)
