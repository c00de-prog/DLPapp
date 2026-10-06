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

The provided single-file SFX release additionally includes:
- Official Python 3.12.10 x64 runtime and Tcl/Tk, extracted from
  https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
  Python LICENSE.txt is included at the runtime root. Tcl/Tk license.terms files
  are retained in their original Tcl directories.
- Official 7-Zip LZMA SDK 23.01 7zSD.sfx self-extractor:
  https://www.7-zip.org/a/lzma2301.7z
  SDK license/source: https://www.7-zip.org/sdk.html
  SDK license text is included in licenses/7zip-lzma.txt.
