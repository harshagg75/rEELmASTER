# skills/EDITOR.md

## Goal
Auto video editing using MoviePy. Convert an EditManifest JSON into a final .mp4 reel ready for upload.

## Files to Build
- `src/tools/auto_editor.py`
  - `render_reel(manifest: EditManifest, output_path: str) → str`
    Reads clips from EditManifest, applies cuts, transitions, overlays, and audio sync.
    Returns path to final rendered .mp4.

## EditManifest Structure
The manifest produced by Agent 07 (edit_spec.py) contains:
- `clips`: ordered list of `{clip_id, start_sec, end_sec, transition_in, transition_out}`
- `audio`: `{audio_id, r2_url, sync_offset_sec}`
- `overlays`: list of `{type, text, start_sec, duration_sec, position}`
- `color_grade`: `{preset}` — e.g. "warm", "cool", "cinematic"
- `aspect_ratio`: always "9:16"
- `target_duration_sec`: final reel length (15–60s)

## MoviePy Implementation Notes
```python
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip, TextClip

# Load + trim each clip
clips = [VideoFileClip(path).subclip(start, end) for path, start, end in segments]

# Concatenate
final = concatenate_videoclips(clips, method="compose")

# Add audio
audio = AudioFileClip(audio_path).subclip(0, final.duration)
final = final.set_audio(audio)

# Export — must match Instagram requirements
final.write_videofile(
    output_path,
    codec="libx264",
    audio_codec="aac",
    fps=30,
    preset="fast",
)
```

## Output Requirements
- Codec: H.264 video + AAC audio
- Resolution: 1080x1920 (9:16)
- FPS: 30
- Max size: 1GB
- Duration: 3–90 seconds

## Color Grade Presets
Apply via moviepy `ColorizeClip` or `LUT` filter:
- `warm`: slight orange lift, increased saturation
- `cool`: slight blue tint, reduced saturation
- `cinematic`: crushed blacks, slightly desaturated mids
- `none`: no grade applied

## Error Handling
- Missing clip file → log error, skip clip, flag in manifest
- Duration mismatch > 2s → log warning, trim/pad to target
- Audio shorter than video → loop audio to fill

## Test command
```bash
python -c "from src.tools.auto_editor import render_reel; print(render_reel(test_manifest, 'outputs/test.mp4'))"
```
Should produce a valid .mp4 at outputs/test.mp4.
