import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description='Build the Windows console EXE with installed tools.')
    parser.add_argument('--tools-dir',type=Path)
    args=parser.parse_args()
    if os.name!='nt': raise SystemExit('Run on Windows with Python 3.10+ x64.')
    tools={}
    for name in ('ffmpeg','ffprobe','deno'):
        candidate=args.tools_dir/(name+'.exe') if args.tools_dir else None
        path=str(candidate) if candidate and candidate.is_file() else shutil.which(name)
        if not path: raise SystemExit('Missing '+name+'.exe. Install it or use --tools-dir PATH.')
        tools[name]=path
    subprocess.run([sys.executable,'-m','pip','install','-e',str(ROOT),'pyinstaller>=6,<7'],check=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
    entry=ROOT/'build/cli_entry.py'
    entry.parent.mkdir(exist_ok=True)
    entry.write_text('from dlpapp_cli.cli import main\nraise SystemExit(main())\n')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--console','--noupx','--name','dlpapp','--collect-all','yt_dlp','--collect-all','yt_dlp_ejs',str(entry)],cwd=ROOT,check=True)
    destination=ROOT/'dist/dlpapp/tools'
    destination.mkdir(exist_ok=True)
    for name,path in tools.items(): shutil.copy2(path,destination/(name+'.exe'))
    for name in ('README.md','THIRD_PARTY.md'): shutil.copy2(ROOT/name,ROOT/'dist/dlpapp'/name)
    print('Distribute the WHOLE dist/dlpapp folder and tool licenses. Add that folder to user PATH.')


if __name__=='__main__': main()
