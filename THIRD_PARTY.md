# Components and sources

The project owner supplies the application license separately. This file does
not assign a license to DLPapp source code. Python/Tkinter and PyInstaller
have separate licenses and exceptions; PyInstaller bundles runtime dependencies.

The build fetches third-party executables from their upstream GitHub releases:

- yt-dlp: https://github.com/yt-dlp/yt-dlp — Unlicense source; official bundled
  Windows executable also contains dependencies with separate licenses.
  See https://github.com/yt-dlp/yt-dlp/blob/master/THIRD_PARTY_LICENSES.txt
- FFmpeg/ffprobe: https://github.com/yt-dlp/FFmpeg-Builds — GPL build.
  Exact downloaded release/asset and source URL are recorded in tools/versions.json;
  license files in the ZIP are copied into tools. Build recipes, patches and
  source archives are provided by the upstream release/project.
- Deno: https://github.com/denoland/deno — MIT and bundled third-party licenses.
  See https://github.com/denoland/deno/blob/main/LICENSE.md
- Python: https://docs.python.org/3/license.html
- Tcl/Tk: https://www.tcl-lang.org/software/tcltk/license.html
- PyInstaller: https://pyinstaller.org/en/stable/license.html

Keep licenses with redistributed binaries and provide corresponding source
for GPL components as required by their licenses. This project does not claim
ownership of upstream binaries. The source ZIP contains no third-party binaries.

The supplied cached-runtime release additionally includes the official Python
3.12.10 x64 runtime and Tcl/Tk, extracted from:
https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
Python LICENSE.txt is retained at the runtime root. Tcl/Tk license.terms files
are retained in their original Tcl directories.

The cache launcher is compiled from native/launcher.c with MinGW-w64. It uses
Windows system APIs and the Windows-provided PowerShell/.NET ZIP extractor;
it does not bundle a 7-Zip SFX module. launcher_blob.py contains the precompiled
launcher, and native/build_launcher.py can regenerate it.
