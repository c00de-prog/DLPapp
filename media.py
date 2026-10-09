"""Format and codec contract, shared by the GUI and tests."""
from i18n import AppError

VIDEO_FORMATS = ('MP4', 'MKV', 'WEBM')
AUDIO_FORMATS = ('MP3', 'M4A', 'WAV', 'FLAC', 'OPUS')
FORMATS = VIDEO_FORMATS + AUDIO_FORMATS
CODECS = {'auto': (), 'h264': ('avc', 'h264'), 'hevc': ('hev', 'hvc', 'h265'),
          'vp9': ('vp9', 'vp09'), 'av1': ('av01', 'av1')}


def available_heights(info, fmt='MKV', codec='auto'):
    """Only list streams that can be remuxed into the chosen container."""
    if fmt in AUDIO_FORMATS:
        return []
    values = set()
    for stream in info.get('formats', []):
        vcodec = stream.get('vcodec') or 'none'
        height = stream.get('height')
        if vcodec == 'none' or not isinstance(height, (int, float)):
            continue
        if codec != 'auto' and not vcodec.startswith(CODECS.get(codec) or ('\0',)):
            continue
        if fmt == 'WEBM' and (stream.get('ext') != 'webm' or not vcodec.startswith(('vp8', 'vp9', 'vp09', 'av01', 'av1'))):
            continue
        if fmt == 'MP4' and not vcodec.startswith(('avc', 'hev', 'hvc', 'h26', 'av01', 'av1')):
            continue
        values.add(int(height))
    return sorted(values, reverse=True)


def format_options(height, fmt, codec='auto'):
    if fmt not in FORMATS or codec not in CODECS:
        raise AppError('unsupported_format')
    if fmt in AUDIO_FORMATS:
        audio = {'MP3': 'mp3', 'M4A': 'm4a', 'WAV': 'wav', 'FLAC': 'flac', 'OPUS': 'opus'}[fmt]
        return ['-f', 'ba/b', '-x', '--audio-format', audio, '--audio-quality', '0']
    height = int(height)
    if height <= 0:
        raise AppError('select_quality')
    video_filter = f'[height={height}]'
    if codec != 'auto':
        prefix = '|'.join(CODECS[codec])
        video_filter += f"[vcodec~='^({prefix})']"
    if fmt == 'MP4':
        video_filter += "[vcodec~='^(avc|hev|hvc|h26|av01|av1)']"
    if fmt == 'WEBM':
        video_filter += '[ext=webm]'
        selector = f'bv{video_filter}+ba[ext=webm]/b{video_filter}/bv{video_filter}'
    elif fmt == 'MP4':
        selector = f'bv{video_filter}+ba[ext=m4a]/bv{video_filter}+ba/b{video_filter}/bv{video_filter}'
    else:
        selector = f'bv{video_filter}+ba/b{video_filter}/bv{video_filter}'
    # Remux also fixes the extension when only a combined stream is available.
    return ['-f', selector, '--merge-output-format', fmt.lower(), '--remux-video', fmt.lower()]
