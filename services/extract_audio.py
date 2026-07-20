import os
import shutil
import subprocess

from config import FFMPEG_BINARY


def _resolve_ffmpeg() -> str:
    """FFmpeg executable'ni PATH yoki FFMPEG_BINARY orqali topadi."""
    if os.path.isabs(FFMPEG_BINARY):
        if os.path.isfile(FFMPEG_BINARY) and os.access(FFMPEG_BINARY, os.X_OK):
            return FFMPEG_BINARY
        raise RuntimeError(f"FFmpeg executable topilmadi: {FFMPEG_BINARY}")

    resolved = shutil.which(FFMPEG_BINARY)
    if not resolved:
        raise RuntimeError(
            "Serverda ffmpeg topilmadi. FFmpeg o'rnating yoki "
            "FFMPEG_BINARY environment variable'ini sozlang."
        )
    return resolved


def extract_audio_from_video(
    video_path: str,
    output_path: str,
    optimize_for_transcription: bool = False,
) -> str:
    """Videodan ishonchli MP3 formatida audio ajratadi."""
    video_path = os.path.abspath(video_path)
    output_path = os.path.abspath(output_path)

    if not os.path.isfile(video_path):
        raise RuntimeError(f"Video fayl topilmadi: {video_path}")
    if os.path.getsize(video_path) == 0:
        raise RuntimeError("Yuklangan video fayli bo'sh.")

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # `.mp3` extension ffmpegga mavjud MP3 encoderni avtomatik tanlatadi;
    # `-acodec mp3` ayrim buildlarda "Unknown encoder" berishi mumkin.
    if optimize_for_transcription:
        audio_options = [
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "64k",
        ]
    else:
        audio_options = ["-q:a", "2"]

    command = [
        _resolve_ffmpeg(),
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-i", video_path,
        "-vn",
        *audio_options,
        "-y",
        output_path,
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Videodan audio ajratish vaqti tugadi.") from exc
    except OSError as exc:
        raise RuntimeError(f"FFmpeg ishga tushmadi: {exc}") from exc

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(
            f"Videodan audio ajratib bo'lmadi (ffmpeg): {error}"
        )

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Videoda audio oqimi topilmadi.")

    return output_path
