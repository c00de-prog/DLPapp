# DLPapp 2.0.1

A lightweight, portable Windows video and audio downloader built with Python, Tkinter, yt-dlp and FFmpeg.

[GitHub](https://github.com/c00de-prog/DLPapp) · [Releases](https://github.com/c00de-prog/DLPapp/releases)

## Download and run

Download **DLPapp.exe** from Releases and run it on **Windows 10/11 x64**. Users do not need to install Python, yt-dlp, FFmpeg or Deno. The EXE can be moved or renamed. Put it in a writable folder if you want automatic in-place application updates.

The first launch extracts the bundled runtime into `%LOCALAPPDATA%\DLPapp\runtime\<runtime-hash>`. Later launches of the same build reuse it. A new build is extracted once again. No administrator privileges are requested.

1. Paste a single video URL and click **Check video**.
2. Select format, source quality and optionally a video codec.
3. Click **Download video**. Progress shows transfer speed and estimated time remaining when provided by yt-dlp.
4. Keep the window open, minimize it, or use **Hide & notify when done**. Clicking the tray icon restores the window. Closing during a download asks whether to keep downloading or stop and exit.

Windows notification settings may suppress balloon notifications. Downloads continue while the window is hidden, but stop when you explicitly exit the application. Playlist and live stream downloads are not supported in this release.

## Formats and codecs

| Output | Behavior |
| --- | --- |
| MP4 | Remux compatible H.264, HEVC or AV1 streams without video re-encoding |
| MKV | Remux the selected source video and audio; broad codec support |
| WebM | Use available WebM VP9/AV1 streams and compatible audio |
| MP3, M4A, WAV, FLAC, Opus | Extract/convert the best source audio with FFmpeg |

The quality list changes with the selected format and codec and uses exact source heights. Codec selection offers Auto, H.264, HEVC, VP9 and AV1 according to the container. A codec must exist in the source: this app does not manufacture missing source streams or claim to support every possible codec. Remuxing preserves source codecs, so playback support depends on the player. Audio-only formats disable the video quality and codec controls.

## Settings

Open **Settings** for Profile, General, Downloads, Updates and About. There is one dark interface and no theme selector.

- Nickname is local, optional and limited to 40 characters.
- Language is Auto, English or Russian. Auto chooses Russian for a Russian Windows UI, English otherwise.
- Ctrl+V, Shift+Insert, the Paste button and the right-click menu work in text fields. Windows Ctrl shortcuts use virtual key codes and work with Russian keyboard layouts.
- Choose a **parent folder** for downloads. DLPapp creates **DDownloads** inside it. With no override, DDownloads is beside the EXE. For example, choosing `D:\Media` saves to `D:\Media\DDownloads`.
- Changing the folder affects future downloads and the history displayed in Downloads. Files already downloaded stay where they are. An active download keeps the folder and format chosen when it started.
- Downloads stores completed file paths, title, format and date. Open a file with the button or double-click. Clearing history does not delete files. History is limited to the most recent 300 entries across all folders.
- The most recently used format, codec and available quality are restored.

Settings and history are stored atomically in `%LOCALAPPDATA%\DLPapp\settings.json` with `"app_id": "DLPapp"`. The previous language-only settings are migrated. Another application's settings are not imported. Moving or replacing the EXE does not reset preferences. Nicknames and history are not sent to GitHub.

## Updates

**DLPapp and yt-dlp updates are separate.** Checks occur at startup if at least 24 hours have elapsed and periodically while the app is running. There is no scheduled task or service running after you exit. Busy downloads defer updates. Both automatic checks can be disabled, and manual buttons are available.

Application checks use:

```
https://api.github.com/repos/c00de-prog/DLPapp/releases/latest
```

A newer stable `vX.Y.Z` release must contain an asset named **DLPapp.exe** and its GitHub-provided SHA256 `digest`. The app shows the new version; **Download & restart** asks for confirmation, downloads with progress to a staging directory, verifies its size, SHA256 and PE header, then starts a short PowerShell helper. The helper waits for the GUI process to exit, backs up the exact old EXE, replaces it in the same location, launches the new EXE and removes the backup after the new GUI confirms successful startup and the expected version (up to three minutes for first extraction). A replacement/start error attempts rollback and writes `%LOCALAPPDATA%\DLPapp\update-error.log`. Settings and downloads are never deleted. This checks startup; it cannot prove that every later download will succeed. Old runtime caches are retained to avoid disrupting other running instances.

The download is staged **before** removing/replacing the old application. Cancelling or a network/hash failure keeps the current app. In source mode or when the outer EXE is unknown, the release page opens instead. The v1 EXE has no self-updater; replace it manually once with v2.

yt-dlp updates use the official `yt-dlp/yt-dlp` latest release, download and verify `yt-dlp.exe`, and store it in `%LOCALAPPDATA%\DLPapp\tools`. That copy overrides bundled yt-dlp and survives application upgrades. FFmpeg, ffprobe and Deno remain bundled and update when you publish a new DLPapp build. GitHub outages, request limits, missing assets or missing hashes are shown in Updates; media downloading remains available with installed tools.

## Build your own EXE

Only the **build computer** needs Windows 10/11 x64 and Python 3.11+ x64 with Tkinter. No C compiler is required for normal builds.

Double-click **build_windows.bat**, or run:

```powershell
py -3 build_exe.py
```

The build creates `.build-env`, installs PyInstaller, runs the test suite, fetches tools if needed, builds a directory runtime and embeds its ZIP behind the compiled native launcher. Output:

```
dist/DLPapp.exe
dist/DLPapp.exe.sha256
```

Refresh bundled tools when building a release:

```powershell
py -3 build_exe.py --refresh-tools
```

Keep your existing license file. The script includes `LICENSE`, `LICENSE.txt`, `LICENSE.md` or `license` if present and does not generate/replace it. See THIRD_PARTY.md for bundled tool licensing. Internet is required to fetch build dependencies and tools.

Optional: run the **Windows portable EXE** GitHub Actions workflow. Download its artifact, unpack it, and attach **DLPapp.exe** and its checksum to a Release. Set `VERSION` in `version.py` before each release and use a matching `vX.Y.Z` tag. Commit the updated source to `main` first. The release EXE must use the exact asset name for automatic update discovery.

## Architecture

| File | Responsibility |
| --- | --- |
| ui.py | Lightweight rounded Tk widgets, cards and sidebar page stack |
| check_updates.py | Read-only diagnostics for the actual release API |
| app.py | Tkinter UI, lazy settings window, event queue, background processes and history controls |
| core.py | Portable paths, tool discovery, URL checking, yt-dlp commands and progress parsing |
| media.py | Formats, compatible source codecs and quality filtering |
| i18n.py | English/Russian strings, system language and localized errors |
| settings.py | Namespaced atomic JSON settings and bounded folder-specific history |
| clipboard.py | Keyboard-layout independent shortcuts and context menus |
| notifications.py | Lazy native Win32 tray icon and completion notifications |
| updates.py | GitHub release discovery, verified downloads, yt-dlp override and staged EXE replacement |
| version.py | Version, author, app identity and official repository |
| bootstrap.py | Entry point for the supplied full Python runtime |
| build_exe.py / package_exe.py | Build and package the runtime into one EXE |
| native/launcher.c | Extract-once Windows launcher; passes original EXE location to the app |
| launcher_blob.py | Compiled launcher bytes so regular builders do not need MinGW |
| setup_tools.py | Fetch bundled yt-dlp, FFmpeg/ffprobe and Deno |
| tests/ | Offline subprocess, format, settings, history, translation and update verification tests |

No webview, Qt, Electron, image downloads or permanent background polling process is used. GUI code and network/process work are separated with a thread-safe queue; worker threads never modify Tk widgets. Video metadata is held only for the selected video; no thumbnail cache is built. Settings widgets are destroyed when closed.

Optional maintainer-only launcher rebuild after editing C (requires MinGW-w64):

```powershell
py -3 native/build_launcher.py
```

## Update testing

See [TEST_UPDATES.md](TEST_UPDATES.md) for a real Windows 2.0.0 → 2.0.1 update test and read-only API diagnostics using `check_updates.py --current 2.0.0`.

## Verification before publishing

Run `python -m unittest discover -s tests -v`. In addition, test the built EXE on Windows:

- First and repeated launch; move and rename the EXE.
- Paste a URL with Russian and English layouts and through the context menu.
- Download video plus audio-only formats; check progress and actual file playback.
- Save nickname, language and folder; restart; change folder and check history.
- Hide during a download and verify a tray notification and restoring the window.
- Check yt-dlp updates and a **newer test application release**, including cancellation and restart with retained settings.

This package's offline tests and Linux GUI checks do not substitute for native Windows acceptance testing of notifications or EXE replacement. Automatic update checks require a public reachable GitHub release. Download only media you are permitted to save.
