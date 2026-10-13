# Validation for CLI 0.1.0

- 13 unit/integration tests passed on Linux (Python 3.12).
- Actual FFmpeg local WAV-to-FLAC extraction passed; existing-file protection passed.
- Built wheel installed into an isolated venv without dependencies for package/entry-point checks.
- Installed `dlpapp --version`, `dlpapp --help` and `dlpapp help` worked from /tmp, outside the project.
- Debian package built and metadata inspected; control declares system Python, yt-dlp and FFmpeg dependencies.
- The wheel and source ZIP passed archive integrity checks.

Limits: downloading real online media, dependency installation from PyPI, actual pipx PATH setup, Debian installation, and macOS/Windows runtime behavior were not verified here. Windows console EXE build script and the three-OS GitHub workflow are provided, not claimed as completed builds. No APT/PyPI publication occurred.

Acceptance checks: install the wheel with pipx; reopen the terminal; run `dlpapp doctor`; run from a different folder; check a public URL; download a short permitted video and extract its audio; test Ctrl+C; verify output and RU/EN settings; test the same on macOS and Windows.
