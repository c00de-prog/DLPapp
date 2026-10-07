"""Optional maintainer task: rebuild launcher_blob.py using MinGW-w64."""
import argparse
import base64
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default='x86_64-w64-mingw32-gcc')
    parser.add_argument('--windres', default='x86_64-w64-mingw32-windres')
    args = parser.parse_args()
    build = ROOT / 'build' / 'native'
    build.mkdir(parents=True, exist_ok=True)
    rc = build / 'launcher.rc'
    rc.write_text(f'1 ICON "{(ROOT / "assets/icon.ico").as_posix()}"\n'
                  f'1 24 "{(ROOT / "native/launcher.manifest").as_posix()}"\n')
    resource = build / 'launcher-res.o'
    subprocess.run([args.windres, '-i', str(rc), '-o', str(resource)], check=True)
    output = build / 'launcher.exe'
    subprocess.run([args.compiler, '-Os', '-s', '-static', '-municode', '-mwindows',
                    '-Wall', '-Wextra', '-Werror', '-Wl,--stack,8388608',
                    str(ROOT / 'native/launcher.c'), str(resource), '-lshell32', '-ladvapi32',
                    '-o', str(output)], check=True)
    blob = base64.b64encode(output.read_bytes()).decode('ascii')
    source = '"""Compiled native/launcher.c (Windows x64), embedded for builds without a C compiler."""\nLAUNCHER_B64 = (\n'
    source += ''.join('    ' + repr(blob[i:i + 100]) + '\n' for i in range(0, len(blob), 100)) + ')\n'
    (ROOT / 'launcher_blob.py').write_text(source, encoding='utf-8')
    print('Updated launcher_blob.py')


if __name__ == '__main__':
    main()
