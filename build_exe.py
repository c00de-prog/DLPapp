"""Build a portable, single-file Windows EXE. Run: python build_exe.py"""
import argparse
import os
import struct
import subprocess
import sys
import venv
import zipfile
import base64
from package_exe import package
from launcher_blob import LAUNCHER_B64
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = 'DLPapp'
TOOLS = ('yt-dlp.exe', 'ffmpeg.exe', 'ffprobe.exe', 'deno.exe')


def run(command):
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-tools', action='store_true', help='Download fresh upstream tools')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Run build_exe.py on Windows 10/11 x64.')
    if sys.version_info < (3, 11) or struct.calcsize('P') != 8:
        raise SystemExit('The build computer needs Python 3.11+ x64 with Tkinter.')
    print('[1/5] Preparing isolated build environment...', flush=True)
    environment = ROOT / '.build-env'
    python = environment / 'Scripts' / 'python.exe'
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    run([python, '-m', 'pip', 'install', '--disable-pip-version-check', 'pyinstaller>=6,<7'])
    run([python, '-c', 'import tkinter'])
    print('[2/5] Running tests...', flush=True)
    run([python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    print('[3/5] Preparing yt-dlp, FFmpeg and Deno...', flush=True)
    if args.refresh_tools or not all((ROOT / 'tools' / name).is_file() for name in TOOLS):
        run([python, ROOT / 'setup_tools.py'])
    else:
        print('Using existing tools. Use --refresh-tools to update them.', flush=True)
    for name in TOOLS:
        flag = '-version' if name.startswith('ff') else '--version'
        subprocess.run([str(ROOT / 'tools' / name), flag], check=True,
                       capture_output=True, timeout=30)
    print('[4/5] Building one EXE...', flush=True)
    command = [python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
               '--windowed', '--name', 'DLPappRuntime', '--noupx',
               '--icon', str(ROOT / 'assets' / 'icon.ico'),
               '--add-data', f'{ROOT / "assets"};assets',
               '--add-data', f'{ROOT / "tools"};tools',
               '--add-data', f'{ROOT / "THIRD_PARTY.md"};.',
               '--add-data', f'{ROOT / "README.md"};.']
    # The user's own license is optional; never generate or replace it.
    for filename in ('LICENSE', 'LICENSE.txt', 'LICENSE.md'):
        if (ROOT / filename).is_file():
            command += ['--add-data', f'{ROOT / filename};.']
    run(command + [ROOT / 'app.py'])
    distribution = ROOT / 'dist'
    archive = ROOT / 'build' / 'runtime.zip'
    runtime = distribution / 'DLPappRuntime'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as stream:
        for path in sorted(runtime.rglob('*')):
            if path.is_file():
                stream.write(path, path.relative_to(distribution))
    launcher = ROOT / 'build' / 'launcher.exe'
    launcher.write_bytes(base64.b64decode(LAUNCHER_B64))
    output = distribution / f'{APP_NAME}.exe'
    package(launcher, archive, output, mode=2)
    with output.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise RuntimeError('The output is not a Windows executable.')
    print('[5/5] Ready:', output, flush=True)
    print('Give users this ONE EXE. Python and tools are included.')
    print('Runtime is cached once per version. Downloads stay beside the EXE.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print('Build failed:', exc, file=sys.stderr)
        sys.exit(1)
