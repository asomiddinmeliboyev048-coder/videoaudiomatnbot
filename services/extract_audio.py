import subprocess


def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """
    Videodan audio (MP3) ajratib oladi — ffmpeg yordamida.
    """
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "mp3",
        "-q:a", "2",
        "-y",
        output_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg xatosi: {result.stderr.decode('utf-8', errors='ignore')}"
        )

    return output_path