import json
import subprocess
from pathlib import Path


def probe_video(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    duration = float(data["format"]["duration"])
    return {
        "durationMs": int(duration * 1000),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": parse_fps(stream.get("r_frame_rate", "24/1")),
    }


def parse_fps(value: str) -> int:
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        denominator_int = int(denominator)
        return round(int(numerator) / denominator_int) if denominator_int else 24
    return round(float(value))
