import shutil
import subprocess
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'


def main():
    if not shutil.which('dpkg-deb'):
        raise SystemExit('Build on Linux with dpkg-deb installed.')
    output = ROOT/'dist'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'package'
        control=root/'DEBIAN'
        control.mkdir(parents=True)
        (control/'control').write_text(f'''Package: dlpapp
Version: {VERSION}
Section: video
Priority: optional
Architecture: all
Maintainer: c00de-prog
Depends: python3 (>= 3.10), yt-dlp, ffmpeg
Description: Terminal interface for video and audio downloads
 DLPapp CLI with an interactive menu, IPv4 and offline audio conversion.
''')
        package=root/'usr/lib/python3/dist-packages/dlpapp_cli'
        shutil.copytree(ROOT/'src/dlpapp_cli',package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        binary=root/'usr/bin/dlpapp'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/usr/bin/python3\nfrom dlpapp_cli.cli import main\nraise SystemExit(main())\n')
        binary.chmod(0o755)
        docs=root/'usr/share/doc/dlpapp'
        docs.mkdir(parents=True)
        for name in ('README.md','THIRD_PARTY.md','LICENSE','LICENSE.txt','LICENSE.md','license'):
            if (ROOT/name).is_file(): shutil.copy2(ROOT/name,docs/name)
        destination=output/f'dlpapp_{VERSION}_all.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','--build',str(root),str(destination)],check=True)
        print(destination)


if __name__=='__main__': main()
