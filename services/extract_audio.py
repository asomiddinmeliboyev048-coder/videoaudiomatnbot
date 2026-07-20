import os
import subprocess


def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """
    Videodan audio ajratadi.

    Transkripsiya uchun `.wav` yoki `.flac` tanlansa, Whisperga sifatli
    kirish berish uchun 16 kHz mono audio yaratiladi. Katta transkripsiya
    audiosi uchun `.m4a` 64 kbit/s ga siqiladi. Foydalanuvchiga yuboriladigan
    `.mp3` esa yuqori sifatda saqlanadi.
    """
    suffix = os.path.splitext(output_path)[1].lower()
    if suffix in {".wav", ".flac"}:
        codec = "pcm_s16le" if suffix == ".wav" else "flac"
        audio_options = [
            "-ac", "1",
            "-ar", "16000",
            "-c:a", codec,
        ]
    elif suffix == ".m4a":
        audio_options = [
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "aac",
            "-b:a", "64k",
        ]
    else:
        audio_options = ["-acodec", "libmp3lame", "-q:a", "2"]

    command = [
        "ffmpeg",
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
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Serverda ffmpeg o'rnatilmagan.") from exc

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(f"Videodan audio ajratib bo'lmadi: {error}")

    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Videoda audio oqimi topilmadi.")

    return output_path
