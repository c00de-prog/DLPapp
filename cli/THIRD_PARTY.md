# Third-party components

- yt-dlp: https://github.com/yt-dlp/yt-dlp (see upstream LICENSE and optional dependency licenses).
- FFmpeg / ffprobe: https://ffmpeg.org/legal.html — license depends on the selected build. Not bundled in the wheel or source archive.
- Deno: https://github.com/denoland/deno — see upstream LICENSE. Not bundled in the wheel or source archive.
- Node.js: https://github.com/nodejs/node — alternative runtime; see upstream LICENSE.
- Python: https://docs.python.org/3/license.html — required for pipx, bundled when building a frozen executable.
- PyInstaller: https://pyinstaller.org/en/stable/license.html — build tool for the optional Windows console distribution.

The Windows builder copies FFmpeg/ffprobe/Deno from your selected tools directory or PATH. Include the respective license files and distribution obligations before releasing that build. No tool binaries are present in this source archive.
