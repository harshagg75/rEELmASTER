import subprocess
import pytest
import static_ffmpeg

# Ensure ffmpeg/ffprobe binaries are on PATH for all tests
static_ffmpeg.add_paths()


@pytest.fixture(scope="session")
def test_clip(tmp_path_factory):
    """
    Minimal 5-second 1080x1920 vertical MP4 (black video + 1kHz sine tone).
    Used as a real file input for ffprobe/ffmpeg tests.
    """
    tmp_dir = tmp_path_factory.mktemp("clips")
    clip_path = tmp_dir / "test_clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=black:size=1080x1920:rate=30:duration=5",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(clip_path), "-y", "-loglevel", "error",
        ],
        check=True,
    )
    return str(clip_path)


@pytest.fixture(scope="session")
def test_clip_vertical(tmp_path_factory):
    """3-second vertical 1080x1920 MP4 (blue background, no audio)."""
    tmp_dir = tmp_path_factory.mktemp("clips_v")
    clip_path = tmp_dir / "test_vertical.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=blue:size=1080x1920:rate=30:duration=3",
            "-c:v", "libx264", "-an",
            str(clip_path), "-y", "-loglevel", "error",
        ],
        check=True,
    )
    return str(clip_path)


@pytest.fixture(scope="session")
def test_clip_horizontal(tmp_path_factory):
    """3-second horizontal 1920x1080 MP4 (landscape, no audio)."""
    tmp_dir = tmp_path_factory.mktemp("clips_h")
    clip_path = tmp_dir / "test_horizontal.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=green:size=1920x1080:rate=30:duration=3",
            "-c:v", "libx264", "-an",
            str(clip_path), "-y", "-loglevel", "error",
        ],
        check=True,
    )
    return str(clip_path)
