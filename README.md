# DLPapp

A simple, portable video downloader for **Windows 10/11 x64**, built with Python and Tkinter.

**Paste a link → check the video → choose an available quality → download.**

The application currently has a **Russian-language interface**. This README is in English.

## Download and run

1. Open the [Releases page](https://github.com/c00de-prog/DLPapp/releases).
2. Download `DLPapp.exe` from the release assets, when available.
3. Save it in a writable folder and double-click it.

**No Python, FFmpeg, yt-dlp or Deno installation is required to run the packaged EXE.**
All required components are included. Startup may take a few seconds while they
are extracted to a temporary folder.

You can move the **single EXE** between folders, drives or USB storage after
closing the application. Downloads are saved in a `Downloads` folder beside the
EXE. The application is not tied to a particular drive or working directory.
Keep the `Downloads` folder with the EXE if you also want to move saved videos.

## Features

- Check a video URL without downloading the video.
- Select resolutions reported by yt-dlp, such as 720p or 1080p.
- Download video with audio when the source has an audio track.
- View download progress, speed and estimated time remaining.
- Cancel an operation or open the output folder.
- Keep the interface responsive through background processing.
- Display the DLPapp logo and application icon.

Separate video and audio streams are merged into **MKV without re-encoding**.
Combined streams retain their original container. The selected resolution is
not silently replaced with a lower one. Cancellation preserves partial files
for a later retry with the same quality.

## Usage

1. Paste a full `http://` or `https://` link to an individual video.
2. Click **Проверить видео** (Check video).
3. Select an available resolution.
4. Click **Скачать видео** (Download video).
5. Wait for **Готово** (Done), then open the `Downloads` folder.

Progress may reach 100% before video and audio have finished merging. Wait for
the completion message before opening or moving the output file.

## Build your own EXE

The **build computer** needs Windows 10/11, **Python 3.11+ x64 with Tkinter**,
and an internet connection. Users of the finished EXE do not need Python.

Clone or download the source, open a terminal in the project folder, and run:

```powershell
python build_exe.py
```

Alternatively, double-click `build_windows.bat`.

The build script:

1. Creates an isolated `.build-env` environment and installs PyInstaller.
2. Runs the tests.
3. Downloads missing Windows tools into `tools` and checks that they run.
4. Bundles Python, the GUI, logo assets and tools into one executable.
5. Checks the output file and prints its location.

The result is:

```text
dist/DLPapp.exe
```

Distribute **only this EXE**. The `.build-env`, `build` and `tools` folders are
not needed separately on the user's computer. Temporary bundled components
are normally removed on exit; downloaded videos remain beside the EXE.

To update the bundled tools and rebuild:

```powershell
python build_exe.py --refresh-tools
```

The executable name is configured with `APP_NAME` in `build_exe.py`.
The window title and displayed application name are configured in `app.py`.

## Run from source

On Windows, prepare the tools and start the application:

```powershell
python setup_tools.py
python app.py
```

The GUI uses the standard-library Tkinter package. PyInstaller is needed only
for building the executable and is installed automatically by the build script.

## Project structure

| File or folder | Purpose |
| --- | --- |
| `app.py` | Tkinter window, UI state, background workers, processes, progress and cancellation. |
| `core.py` | URL validation, portable paths, available resolutions, yt-dlp commands and progress parsing. |
| `setup_tools.py` | Downloads upstream Windows tools, verifies SHA-256 when a digest is provided by the GitHub API, extracts binaries and records tool versions. |
| `build_exe.py` | Prepares the build environment, runs tests and creates a portable EXE. |
| `build_windows.bat` | Starts the build script with a double-click. |
| `assets/` | SVG/PNG logo and Windows ICO icon. |
| `tests/` | Tests for URLs, quality selection, paths and local worker processes. |
| `THIRD_PARTY.md` | Third-party component sources and licensing information. |
| `.gitignore` | Excludes environments, downloaded tools, user downloads and build output from Git. |
| `.github/workflows/build.yml` | Manual Windows build workflow for GitHub Actions. |

## How it works

### Checking a video

The GUI receives the URL, and `core.py` validates it and builds a yt-dlp command.
A worker thread runs yt-dlp with `--dump-single-json` and `--skip-download`.
The returned JSON provides video metadata and the available resolutions, which
are displayed in the quality selector.

### Downloading

`core.py` builds a format selector for the exact chosen resolution. yt-dlp
downloads the streams, and FFmpeg merges separate video and audio when needed.
Deno supplies the JavaScript runtime used by yt-dlp for supported sites.

The worker sends events through `queue.Queue`. The main thread reads them with
Tkinter's `after()` callback and updates the widgets. The worker never updates
Tkinter directly. On Windows, cancellation terminates the yt-dlp process tree.
The application reports completion only after the process exits successfully
and the output file is found.

### Portability

In a PyInstaller build, `core.app_dir()` uses `sys.executable` to locate the
EXE's folder, while `sys._MEIPASS` identifies the extracted bundled components.
This keeps permanent downloads separate from temporary runtime files.

The separately supplied initial EXE uses a 7-Zip SFX package with portable
Python. `build_exe.py` builds subsequent EXEs with PyInstaller. Both packages
include the required runtime and tools in one file.

## Tests

Run from the project folder:

```powershell
python -m unittest discover -s tests -v
```

The tests use local data and subprocesses; they do not contact YouTube.
Eleven tests passed in the development environment. Python syntax, GUI window
creation on Linux and the supplied EXE archive's integrity were also checked.
**The supplied EXE has not yet been run on native Windows, and the Windows
PyInstaller build has not yet been executed in the development environment.**
These checks do not establish that real downloads work on every supported site.

## Build with GitHub Actions

1. Put the project files in the repository root.
2. Open **Actions → Windows portable EXE → Run workflow**.
3. Select the branch containing the application source and run the workflow.
4. After a successful build, download **DLPapp-Windows-x64** from **Artifacts**.
5. Extract `DLPapp.exe` from the downloaded artifact.

GitHub Actions provides the Windows build environment, so you do not need
Python installed on your own computer for this method.

## License

The application license is maintained by the project owner. Keep the existing
`LICENSE`, `LICENSE.txt` or `LICENSE.md` in the repository root. The build script
includes it when present without modifying its contents.

Third-party components retain their own licenses. See [THIRD_PARTY.md](THIRD_PARTY.md).

## Limitations

- Individual videos only; playlists and live streams are not supported.
- The output folder beside the EXE must be writable.
- Private videos, sign-in requirements, regional restrictions, bot checks or
  website changes may prevent checking or downloading a video.
- Cookie authentication is not implemented.
- Available resolutions depend on what yt-dlp can retrieve from the source.

Download content only when you have permission to do so.
