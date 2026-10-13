"""Commands use argv arrays, never a shell; no GUI or Windows cache dependency."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

VIDEO_FORMATS = ('mp4', 'mkv', 'webm')
AUDIO_FORMATS = ('mp3', 'm4a', 'wav', 'flac', 'opus')


def validate_url(value):
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use a complete HTTP(S) video URL without credentials.')
    return value


def quality(value):
    if value.lower() == 'best':
        return 'best'
    value = value.lower().removesuffix('p')
    if not value.isdecimal() or not 1 <= int(value) <= 16384:
        raise ValueError('Quality must be best or a height such as 720 or 1080p.')
    return str(int(value))


def tool(name, config):
    suffix = '.exe' if os.name == 'nt' else ''
    candidates = []
    if config.get('tools_dir'):
        candidates.append(Path(config['tools_dir']).expanduser() / (name + suffix))
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).parent / 'tools' / (name + suffix))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return shutil.which(name)


def downloader():
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--_yt-dlp']
    if importlib.util.find_spec('yt_dlp') is None:
        raise RuntimeError('yt-dlp is missing. Reinstall with pipx or install the Debian yt-dlp package.')
    return [sys.executable, '-m', 'yt_dlp']


def base(config):
    args = downloader() + ['--ignore-config', '--no-playlist', '--no-colors', '--encoding', 'utf-8',
                           '--socket-timeout', '20', '--retries', '3', '--extractor-retries', '2']
    network = config.get('network', 'ipv4')
    if network == 'ipv4':
        args += ['--force-ipv4']
    elif network == 'ipv6':
        args += ['--force-ipv6']
    ffmpeg = tool('ffmpeg', config)
    if ffmpeg:
        args += ['--ffmpeg-location', str(Path(ffmpeg).parent)]
    for runtime in ('deno', 'node'):
        executable = tool(runtime, config)
        if executable:
            args += ['--js-runtimes', runtime + ':' + executable]
            break
    return args


def require_media_tools(config):
    missing = [name for name in ('ffmpeg', 'ffprobe') if not tool(name, config)]
    if missing:
        raise RuntimeError('Missing ' + ', '.join(missing) + '. Install FFmpeg or run dlpapp config --tools-dir PATH. Run dlpapp doctor for details.')


def selector(height='best', container='mp4', codec='auto'):
    height = quality(height)
    filters = '' if height == 'best' else '[height<=' + height + ']'
    prefixes = {'h264': 'avc|h264', 'hevc': 'hev|hvc|h265', 'vp9': 'vp9|vp09', 'av1': 'av01|av1'}
    if codec != 'auto':
        if codec not in prefixes:
            raise ValueError('Unsupported codec')
        filters += "[vcodec~='^(" + prefixes[codec] + ")']"
    if container == 'mp4':
        filters += "[vcodec~='^(avc|h264|hev|hvc|h265|av01|av1)']"
        # Keep MP4 audio compatible; do not silently choose incompatible streams.
        return f'bv{filters}+ba[ext=m4a]/b{filters}[ext=mp4]'
    if container == 'webm':
        filters += '[ext=webm]'
        return f'bv{filters}+ba[ext=webm]/b{filters}'
    if container != 'mkv':
        raise ValueError('Unsupported video format')
    return f'bv{filters}+ba/b{filters}'


def command(config, url, folder, kind, fmt, height='best', codec='auto', verbose=False):
    url = validate_url(url)
    args = base(config)
    if verbose:
        args += ['--verbose']
    if kind == 'audio':
        if fmt not in AUDIO_FORMATS:
            raise ValueError('Unsupported audio format')
        args += ['-f', 'ba/b', '-x', '--audio-format', fmt, '--audio-quality', '0']
    else:
        args += ['-f', selector(height, fmt, codec), '--merge-output-format', fmt, '--remux-video', fmt]
    return args + ['--newline', '--no-overwrites', '--windows-filenames', '-P', str(folder),
                   '-o', '%(title).160B [%(id)s].%(ext)s', '--', url]


def run(args, capture=False):
    env = os.environ.copy()
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        return subprocess.run(args, env=env, text=True, encoding='utf-8', errors='replace',
                              stdout=subprocess.PIPE if capture else None,
                              stderr=None, check=False)
    finally:
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))


def info(config, url, verbose=False):
    args = base(config)
    if verbose:
        args += ['--verbose']
    result = run(args + ['--dump-single-json', '--skip-download', '--', validate_url(url)], capture=True)
    if result.returncode:
        raise RuntimeError('yt-dlp could not check this URL (exit ' + str(result.returncode) + '). See the message above.')
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or data.get('entries') is not None or data.get('_type') in ('playlist', 'multi_video'):
        raise ValueError('Only individual videos are supported.')
    return data
