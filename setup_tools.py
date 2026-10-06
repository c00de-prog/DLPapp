"""Fetch official upstream Windows x64 binaries into a portable tools folder."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / 'tools'
HEADERS = {'User-Agent': 'DLPapp-builder', 'Accept': 'application/vnd.github+json'}


def fetch(url, target):
    print('Download:', target.name, flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as response:
        with target.open('wb') as output:
            shutil.copyfileobj(response, output)


def release(repo, tag=None):
    endpoint = 'latest' if tag is None else 'tags/' + tag
    with urllib.request.urlopen(urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases/{endpoint}', headers=HEADERS), timeout=60) as response:
        return json.load(response)


def asset(data, name):
    return next(x for x in data['assets'] if x['name'] == name)


def get_asset(item, target):
    temporary = target.with_suffix(target.suffix + '.tmp')
    try:
        fetch(item['browser_download_url'], temporary)
        digest = item.get('digest')
        if digest and digest.startswith('sha256:'):
            sha = hashlib.sha256()
            with temporary.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    sha.update(chunk)
            if sha.hexdigest() != digest.split(':', 1)[1]:
                raise RuntimeError('Checksum mismatch: ' + item['name'])
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def copy_zip_member(archive, basename, target):
    members = [x for x in archive.namelist() if Path(x).name == basename]
    if len(members) != 1:
        raise RuntimeError('Cannot locate unique archive member: ' + basename)
    with archive.open(members[0]) as source, target.open('wb') as destination:
        shutil.copyfileobj(source, destination)


def main(allow_cross=False):
    if not allow_cross and os.name != 'nt':
        raise SystemExit('Run this setup on Windows x64.')
    TOOLS.mkdir(exist_ok=True)
    versions = {}
    with tempfile.TemporaryDirectory(prefix='dlpapp-') as temp:
        work = Path(temp)
        data = release('yt-dlp/yt-dlp')
        get_asset(asset(data, 'yt-dlp.exe'), TOOLS / 'yt-dlp.exe')
        versions['yt-dlp'] = data['tag_name']
        data = release('denoland/deno')
        get_asset(asset(data, 'deno-x86_64-pc-windows-msvc.zip'), work / 'deno.zip')
        with zipfile.ZipFile(work / 'deno.zip') as archive:
            copy_zip_member(archive, 'deno.exe', TOOLS / 'deno.exe')
        versions['deno'] = data['tag_name']
        data = release('yt-dlp/FFmpeg-Builds', 'latest')
        candidates = [x for x in data['assets'] if x['name'].endswith('.zip')
                      and 'win64' in x['name'] and 'gpl' in x['name'] and 'shared' not in x['name']]
        if not candidates:
            raise RuntimeError('FFmpeg Windows x64 ZIP asset not found.')
        item = sorted(candidates, key=lambda x: ('lgpl' in x['name'], 'master' not in x['name'], x['name']))[0]
        get_asset(item, work / 'ffmpeg.zip')
        with zipfile.ZipFile(work / 'ffmpeg.zip') as archive:
            for name in ('ffmpeg.exe', 'ffprobe.exe'):
                copy_zip_member(archive, name, TOOLS / name)
            for member in archive.namelist():
                if not member.endswith('/') and Path(member).name.upper().startswith(('LICENSE', 'COPYING')):
                    dest = TOOLS / ('ffmpeg-' + Path(member).name)
                    with archive.open(member) as src, dest.open('wb') as out:
                        shutil.copyfileobj(src, out)
        versions['ffmpeg'] = {'release': data['tag_name'], 'asset': item['name'],
                              'source': 'https://github.com/yt-dlp/FFmpeg-Builds',
                              'release_url': data['html_url']}
    for name in (() if os.name != 'nt' else ('yt-dlp', 'ffmpeg', 'ffprobe', 'deno')):
        flag = '-version' if name.startswith('ff') else '--version'
        subprocess.run([str(TOOLS / (name + '.exe')), flag], check=True, capture_output=True, timeout=30)
    licenses = TOOLS / 'licenses'
    licenses.mkdir(exist_ok=True)
    for name, url in (
        ('yt-dlp-LICENSE', 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/LICENSE'),
        ('yt-dlp-THIRD_PARTY_LICENSES.txt', 'https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/THIRD_PARTY_LICENSES.txt'),
        ('deno-LICENSE.md', 'https://raw.githubusercontent.com/denoland/deno/main/LICENSE.md'),
    ):
        fetch(url, licenses / name)
    (TOOLS / 'versions.json').write_text(json.dumps(versions, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Tools ready.')


if __name__ == '__main__':
    main('--download-windows' in sys.argv)
