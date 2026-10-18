"""Official GitHub updates: HTTPS, bounded reads, SHA256, staged replacement."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from i18n import AppError, settings_path
from version import RELEASE_API, REPOSITORY, VERSION

DAY = 24 * 60 * 60
HEADERS = {'User-Agent': 'DLPapp/' + VERSION, 'Accept': 'application/vnd.github+json'}


def due(last, now=None):
    now = time.time() if now is None else now
    return not last or now < last or now - last >= DAY


def version_key(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Expected a stable x.y.z version')
    return tuple(map(int, match.groups()))


def official_url(value, repo):
    parsed = urlsplit(value)
    return (parsed.scheme == 'https' and parsed.netloc == 'github.com'
            and parsed.path.startswith('/' + repo + '/releases/')
            and not parsed.username and not parsed.password)


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(4 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise AppError('no_release') from exc
        if exc.code in (403, 429):
            raise AppError('rate_limit') from exc
        raise
    if len(data) > 4 * 1024 * 1024:
        raise AppError('invalid_release')
    return json.loads(data)


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    asset: str
    size: int
    digest: str
    repo: str


def parse_release(data, repo=REPOSITORY, asset_name='DLPapp.exe', compare=True, current_version=None):
    if not isinstance(data, dict) or data.get('draft') or data.get('prerelease'):
        return None
    tag = data.get('tag_name', '')
    if compare:
        try:
            if version_key(tag) <= version_key(current_version or VERSION):
                return None
        except (ValueError, TypeError):
            raise AppError('invalid_release')
    if not official_url(data.get('html_url', ''), repo):
        raise AppError('invalid_release')
    for asset in data.get('assets', []):
        if asset.get('name') != asset_name:
            continue
        url = asset.get('browser_download_url', '')
        digest = asset.get('digest') or ''
        size = asset.get('size')
        if not official_url(url, repo) or not isinstance(size, int) or not 0 < size <= 1024**3:
            raise AppError('invalid_release')
        # GitHub publishes SHA256 for uploaded assets. Refuse unverifiable binaries.
        if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            raise AppError('missing_digest')
        return Release(tag.lstrip('v'), data['html_url'], url, size, digest[7:].lower(), repo)
    raise AppError('missing_asset', name=asset_name)


def check_app():
    return parse_release(get_json(RELEASE_API))


def download_asset(release, destination, callback=None, cancel=None):
    """No changes to the installed file until length, hash and PE header pass."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + '.part')
    try:
        if not official_url(release.asset, release.repo):
            raise AppError('invalid_release')
        req = urllib.request.Request(release.asset, headers={'User-Agent': HEADERS['User-Agent']})
        digest, count, started = hashlib.sha256(), 0, time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as response, temp.open('wb') as stream:
            if urlsplit(response.geturl()).scheme != 'https':
                raise AppError('invalid_release')
            while True:
                if cancel and cancel.is_set():
                    raise AppError('update_cancelled')
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > release.size:
                    raise AppError('hash_failed')
                stream.write(chunk)
                digest.update(chunk)
                if callback:
                    callback(count * 100 / release.size, count / max(time.monotonic() - started, .01))
            stream.flush()
            os.fsync(stream.fileno())
        if count != release.size or digest.hexdigest() != release.digest:
            raise AppError('hash_failed')
        with temp.open('rb') as stream:
            if stream.read(2) != b'MZ':
                raise AppError('hash_failed')
        temp.replace(destination)
        return destination
    finally:
        temp.unlink(missing_ok=True)


def update_ytdlp():
    if os.name != 'nt':
        raise AppError('windows_only')
    repo = 'yt-dlp/yt-dlp'
    release = parse_release(get_json('https://api.github.com/repos/' + repo + '/releases/latest'),
                            repo, 'yt-dlp.exe', compare=False)
    folder = settings_path().parent / 'tools'
    folder.mkdir(parents=True, exist_ok=True)
    version_file = folder / 'yt-dlp.version'
    output = folder / 'yt-dlp.exe'
    try:
        if output.is_file() and version_file.read_text().strip() == release.version:
            return release.version
    except OSError:
        pass
    download_asset(release, folder / 'yt-dlp.new.exe')
    (folder / 'yt-dlp.new.exe').replace(output)
    version_file.write_text(release.version, encoding='utf-8')
    return release.version


def executable_path():
    if os.environ.get('DLPAPP_EXE'):
        return Path(os.environ['DLPAPP_EXE']).resolve()
    if getattr(sys, 'frozen', False) and not os.environ.get('DLPAPP_RUNTIME'):
        return Path(sys.executable).resolve()
    return None


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def restart_environment(environment=None):
    """An independent restart must not inherit a frozen application's runtime."""
    env = dict(os.environ if environment is None else environment)
    drop = {'_MEIPASS2', 'DLPAPP_EXE', 'DLPAPP_HOME', 'DLPAPP_RUNTIME',
            'DLPAPP_UPDATE_ACK', 'DLPAPP_UPDATE_TOKEN', 'PYTHONHOME', 'PYTHONPATH',
            'TCL_LIBRARY', 'TK_LIBRARY'}
    for key in list(env):
        if key.upper().startswith('_PYI_') or key.upper() in drop:
            env.pop(key, None)
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return env


def install_script(source, target, pid, expected_hash, expected_version=VERSION, timeout_seconds=300, show_errors=True):
    """Verified replacement with a per-attempt acknowledgement and safe rollback.

    Never remove the settings, runtime cache, downloads or an existing backup.
    Never delete a new EXE merely because its GUI has not acknowledged startup.
    """
    nonce = uuid.uuid4().hex
    source, target = Path(source), Path(target)
    ack = source.parent / ('install-' + nonce + '.ready.json')
    digest = str(expected_hash).lower()
    if not re.fullmatch('[a-f0-9]{64}', digest):
        raise ValueError('Expected a SHA256 digest')
    if not 1 <= int(timeout_seconds) <= 1800:
        raise ValueError('Invalid startup timeout')
    return f'''$ErrorActionPreference = 'Stop'
$src = {ps_literal(source)}
$dst = {ps_literal(target)}
$bak = $dst + '.dlpapp-backup-{nonce}'
$failed = $dst + '.dlpapp-failed-{nonce}'
$log = {ps_literal(settings_path().parent / 'update-error.log')}
$trace = {ps_literal(settings_path().parent / 'update-install.log')}
$ack = {ps_literal(ack)}
$token = '{nonce}'
$expectedHash = '{digest}'
$changed = $false
$mutex = New-Object System.Threading.Mutex($false, 'Local\\DLPappUpdateInstaller')
$locked = $false
function Trace([string]$message) {{
  try {{ Add-Content -LiteralPath $trace -Value ((Get-Date -Format o) + ' ' + $message) -Encoding UTF8 }} catch {{}}
}}
try {{
  try {{ $locked = $mutex.WaitOne(0) }} catch [System.Threading.AbandonedMutexException] {{ $locked = $true }}
  if (-not $locked) {{ throw 'Another DLPapp update is running. Wait for it to finish.' }}
  Trace 'Starting verified installation'
  if ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {{ throw 'SHA256 mismatch before install' }}
  $parent = Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue
  if ($parent) {{ Wait-Process -Id {int(pid)} -Timeout 120 }}
  Trace 'Old GUI exited; replacing executable'
  for ($attempt = 0; $attempt -lt 60; $attempt++) {{
    try {{ Move-Item -LiteralPath $dst -Destination $bak; $changed = $true; break }}
    catch {{ if ($attempt -eq 59) {{ throw }}; Start-Sleep -Milliseconds 500 }}
  }}
  # Copy keeps the verified download available for recovery.
  Copy-Item -LiteralPath $src -Destination $dst
  if ((Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {{ throw 'SHA256 mismatch after install' }}
  Get-ChildItem Env: | Where-Object {{ $_.Name -like '_PYI_*' }} | ForEach-Object {{ [Environment]::SetEnvironmentVariable($_.Name, $null, 'Process') }}
  foreach ($name in @('_MEIPASS2','DLPAPP_EXE','DLPAPP_HOME','DLPAPP_RUNTIME','PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY')) {{
    [Environment]::SetEnvironmentVariable($name, $null, 'Process')
  }}
  $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
  $env:DLPAPP_UPDATE_ACK = $ack
  $env:DLPAPP_UPDATE_TOKEN = $token
  Trace 'Starting independent new launcher'
  $child = Start-Process -FilePath $dst -WorkingDirectory ([IO.Path]::GetDirectoryName($dst)) -PassThru
  $ready = $false
  $clock = [Diagnostics.Stopwatch]::StartNew()
  while ($clock.Elapsed.TotalSeconds -lt {int(timeout_seconds)}) {{
    if (Test-Path -LiteralPath $ack) {{
      try {{
        $state = Get-Content -LiteralPath $ack -Raw -Encoding UTF8 | ConvertFrom-Json
        $sameExe = [string]::Equals([string]$state.exe, $dst, [StringComparison]::OrdinalIgnoreCase)
        $gui = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
        if ($state.app_id -eq 'DLPapp' -and $state.version -eq {ps_literal(expected_version)} -and $state.token -eq $token -and $sameExe -and $gui) {{ $ready = $true; break }}
      }} catch {{ Trace 'Acknowledgement not ready yet' }}
    }}
    $child.Refresh()
    # The native launcher exits after spawning the runtime; exit 0 alone is not success.
    if ($child.HasExited -and $child.ExitCode -ne 0) {{ throw 'New launcher failed; check startup errors and Windows Protection History' }}
    Start-Sleep -Milliseconds 250
  }}
  if (-not $ready) {{ throw 'The new GUI did not confirm startup within {int(timeout_seconds)} seconds. See update-startup.log and update-install.log.' }}
  Trace 'New GUI confirmed; installation succeeded'
  Remove-Item -LiteralPath $bak -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $ack -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $log -ErrorAction SilentlyContinue
}} catch {{
  $failure = $_ | Out-String
  Trace ('FAILED: ' + $failure)
  if ($changed -and (Test-Path -LiteralPath $bak)) {{
    try {{
      if (Test-Path -LiteralPath $dst) {{ Move-Item -LiteralPath $dst -Destination $failed }}
      Move-Item -LiteralPath $bak -Destination $dst
      Trace 'Old EXE restored; failed EXE preserved separately'
    }} catch {{
      $failure += "`r`nRollback could not finish (the new EXE may still be running). Close DLPapp before manual recovery. Backup preserved: " + $bak + "`r`n" + ($_ | Out-String)
      Trace 'Rollback blocked; backup retained'
    }}
  }}
  $failure | Set-Content -LiteralPath $log -Encoding UTF8
  if (${str(bool(show_errors)).lower()}) {{
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show('DLPapp update failed. Your settings were preserved. See: ' + $log, 'DLPapp') | Out-Null
  }}
}} finally {{
  if ($locked) {{ $mutex.ReleaseMutex() }}
  $mutex.Dispose()
}}
'''


def schedule_install(source, target, digest, expected_version=VERSION):
    if os.name != 'nt':
        raise AppError('windows_only')
    source, target = Path(source).resolve(), Path(target).resolve()
    if not target.is_file() or source == target or target.suffix.lower() != '.exe':
        raise AppError('invalid_release')
    # Test write permission before shutting down the existing application.
    with tempfile.TemporaryFile(dir=target.parent):
        pass
    script = settings_path().parent / 'updates' / ('install-' + str(os.getpid()) + '.ps1')
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(install_script(source, target, os.getpid(), digest, expected_version), encoding='utf-8-sig')
    powershell = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    # PowerShell is a system program: do not inherit the bundled DLL directory.
    frozen = getattr(sys, 'frozen', False)
    if frozen:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        subprocess.Popen([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                          '-File', str(script)], creationflags=subprocess.CREATE_NO_WINDOW,
                         cwd=str(target.parent), env=restart_environment())
    finally:
        if frozen:
            ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
