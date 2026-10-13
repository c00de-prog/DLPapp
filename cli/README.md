# DLPapp CLI 0.1.0

A separate terminal edition of DLPapp for macOS, Linux and Windows. It does not modify the desktop application's settings or releases.

## Install from the wheel

Requires Python 3.10+, pipx, FFmpeg (including ffprobe), and for full YouTube support Deno (recommended) or a supported Node.js version. The wheel installs yt-dlp and its default Python dependencies; it does not bundle FFmpeg or Deno.

```sh
pipx install ./dlpapp_cli-0.1.0-py3-none-any.whl
pipx ensurepath
```

Open a new terminal. Then `dlpapp` works from any working directory and opens the menu. If it is not found, follow the PATH instructions from `pipx ensurepath`. The installed package name is **dlpapp-cli**; its command is **dlpapp**.

macOS, if Homebrew is already installed:

```sh
brew install python pipx ffmpeg deno
pipx install ./dlpapp_cli-0.1.0-py3-none-any.whl
pipx ensurepath
```

Windows with Python and pipx:

```powershell
py -m pip install --user pipx
py -m pipx install .\dlpapp_cli-0.1.0-py3-none-any.whl
py -m pipx ensurepath
```

Install FFmpeg and Deno separately from their official distributions, or point DLPapp to their folder: `dlpapp config --tools-dir "PATH"`. Both ffmpeg and ffprobe are required for downloads. A folder can contain tools or they can be resolved from PATH.

## Commands

```sh
dlpapp
dlpapp --version
dlpapp doctor
dlpapp info "https://www.youtube.com/watch?v=VIDEO_ID"
dlpapp download "URL" --quality 720 --format mp4
dlpapp download "URL" --quality best --format mkv --codec av1 -o "~/Videos"
dlpapp audio "URL" --format mp3
dlpapp convert "local-video.mp4" --format flac -o "~/Music"
dlpapp config --nickname Shoxi --language ru
dlpapp config --network auto
dlpapp help
```

Quality is a **maximum source height**. `--quality 720` chooses the best compatible stream up to 720p and does not upscale. MP4 selects MP4-compatible codecs and M4A audio. If no compatible stream exists, yt-dlp reports an error; try MKV. WEBM selects WebM streams. Audio formats: MP3, M4A, WAV, FLAC, Opus.

Downloads default to `~/Downloads/DDownloads`. `--output` is the exact output folder and does not append DDownloads. Stored paths are made absolute when configured, so they work from any directory. Existing files are not overwritten. Ctrl+C stops an operation; yt-dlp may keep partial files to resume.

IPv4 is enabled by default; `--network auto` or `ipv6` can override it per download. This mitigates one observed slow-network scenario, not every delay. Use `info --verbose` for troubleshooting. Site support is determined by yt-dlp; login/age restrictions and cookie import are not handled by this first release.

The interactive menu is RU/EN based on settings/system language; argparse and upstream tool errors may be in English. There is no GUI, tray, background daemon, persistent yt-dlp connection, in-app EXE updater, or automatic credential collection.

## Debian / Ubuntu

```sh
sudo apt install ./dlpapp_0.1.0_all.deb
dlpapp doctor
```

The package uses distribution Python, yt-dlp and FFmpeg. Deno is a separate requirement for full YouTube support. Older distro yt-dlp releases may not support current YouTube or `--js-runtimes`; prefer the pipx wheel if the distro package is outdated. Do not replace system Python packages with pip.

**No APT repository has been published.** `sudo apt install dlpapp` without a local filename will not work until a repository containing that package is configured. macOS and Windows do not use APT.

## Updates

For a new local wheel:

```sh
pipx install --force ./dlpapp_cli-VERSION-py3-none-any.whl
```

To update only yt-dlp in the pipx environment:

```sh
pipx runpip dlpapp-cli install -U "yt-dlp[default]"
```

`pipx upgrade dlpapp-cli` or `pipx install dlpapp-cli` from PyPI is available only after you publish the package there. GitHub install examples are valid only after you upload this source to your repository. For a separate folder in the existing repo: `pipx install 'git+https://github.com/c00de-prog/DLPapp.git#subdirectory=cli'` after the package is committed at `cli/`.

## Build and test

```sh
python -m pip install build
python -m build
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/build_deb.py
```

Windows PowerShell test command: `$env:PYTHONPATH="src"; python -m unittest discover -s tests -v`.

The Windows console EXE can be built on Windows via `python scripts/build_windows.py`. It packages Python/yt-dlp and copies already-installed FFmpeg/ffprobe/Deno into a portable folder; it does not silently download tool binaries. The GitHub workflow builds the wheel and Debian package and validates the wheel on all three OS families. Executables for Windows/macOS have not been generated or verified in this Linux environment.

### Add CLI to the existing GitHub repo

Keep the GUI files intact. Copy this project into a new `cli/` folder. Put the CLI workflow from this project's `.github/workflows/cli.yml` into the repository-root `.github/workflows/cli.yml` and set the workflow working directory to `cli` as described in that file.

## Licensing and safety

This archive does not replace or invent your project's license. Add your existing license before publishing this package. yt-dlp, FFmpeg and JavaScript runtimes have their own licenses; see THIRD_PARTY.md. Only download content you are authorized to access. An antivirus detection must be investigated; lack of detections is not a safety guarantee.
