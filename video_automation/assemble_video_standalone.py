#!/usr/bin/env python3
"""
Standalone video assembler — creates a FilterMate presentation video from
generated PNG diagrams + MP3 narrations using FFmpeg.

No QGIS or OBS required. Just Python + FFmpeg.
Output: A diagram-based video with narration for each sequence.
"""
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(__file__)
DIAGRAMS_DIR = os.path.join(BASE_DIR, "output", "diagrams", "png")
NARRATION_DIR = os.path.join(BASE_DIR, "output", "narration")
FINAL_DIR = os.path.join(BASE_DIR, "output", "final")
CLIPS_DIR = os.path.join(BASE_DIR, "output", "clips")

# Map sequences to their diagrams and narration files
SEQUENCE_MAP = [
    {
        "id": "seq00_intro",
        "title": "Introduction",
        "diagrams": ["01_positioning"],
        "narrations": ["seq00_intro"],
        "fallback_duration": 8,
    },
    {
        "id": "seq01_problem",
        "title": "Le Problème",
        "diagrams": ["01_positioning"],
        "narrations": ["seq01_problem"],
        "fallback_duration": 15,
    },
    {
        "id": "seq02_install",
        "title": "Installation",
        "diagrams": ["02_backends"],
        "narrations": ["seq02_install"],
        "fallback_duration": 10,
    },
    {
        "id": "seq03_interface",
        "title": "Interface",
        "diagrams": ["03_interface"],
        "narrations": ["seq03_interface"],
        "fallback_duration": 12,
    },
    {
        "id": "seq04_filtering",
        "title": "Demo Filtrage",
        "diagrams": ["04_workflow", "05_predicates"],
        "narrations": ["seq04_filtering_part1", "seq04_filtering_part2", "seq04_filtering_part3"],
        "fallback_duration": 40,
    },
    {
        "id": "seq05_exploration",
        "title": "Exploration",
        "diagrams": ["06_raster"],
        "narrations": ["seq05_exploration"],
        "fallback_duration": 15,
    },
    {
        "id": "seq06_export",
        "title": "Export GeoPackage",
        "diagrams": ["07_export"],
        "narrations": ["seq06_export"],
        "fallback_duration": 20,
    },
    {
        "id": "seq07_backends",
        "title": "Multi-Backend",
        "diagrams": ["08_backends"],
        "narrations": ["seq07_backends"],
        "fallback_duration": 15,
    },
    {
        "id": "seq08_architecture",
        "title": "Architecture",
        "diagrams": ["09_architecture", "10_patterns"],
        "narrations": ["seq08_architecture"],
        "fallback_duration": 15,
    },
    {
        "id": "seq09_advanced",
        "title": "Avancé",
        "diagrams": ["11_undo_redo", "12_metrics"],
        "narrations": ["seq09_advanced"],
        "fallback_duration": 15,
    },
    {
        "id": "seq10_conclusion",
        "title": "Conclusion",
        "diagrams": ["01_positioning"],
        "narrations": ["seq10_conclusion"],
        "fallback_duration": 8,
    },
]


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration using FFprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def create_title_card(title: str, output_path: str, duration: float = 3.0) -> bool:
    """Create a title card video using FFmpeg."""
    # Dark background with white text
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=#1a1a2e:s=1920x1080:d={duration}",
        "-vf", (
            f"drawtext=text='{title}'"
            f":fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2"
            f":font='Segoe UI':borderw=2:bordercolor=#4CAF50,"
            f"drawtext=text='FilterMate v4.6.1'"
            f":fontcolor=#8892b0:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+80"
            f":font='Segoe UI'"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", str(duration),
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [WARNING] Title card failed: {e.stderr.decode()[:200]}")
        return False


def create_clip_from_diagram(diagram_path: str, audio_path: str, output_path: str,
                              duration: float = None) -> bool:
    """Create a video clip from a PNG diagram + audio narration."""
    if not os.path.exists(diagram_path):
        print(f"    [WARNING] Diagram not found: {diagram_path}")
        return False
    
    cmd = ["ffmpeg", "-y"]
    
    # Input: loop the diagram image
    cmd.extend(["-loop", "1", "-i", diagram_path])
    
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        # Video + audio, duration from audio + 1s padding
        audio_dur = get_audio_duration(audio_path)
        total_dur = audio_dur + 1.5 if audio_dur > 0 else (duration or 5)
        cmd.extend([
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-t", str(total_dur),
            output_path
        ])
    else:
        # Video only
        total_dur = duration or 5
        cmd.extend([
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-t", str(total_dur),
            output_path
        ])
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [WARNING] Clip creation failed: {e.stderr.decode()[:300]}")
        return False


def concat_audio_files(audio_paths: list, output_path: str) -> bool:
    """Concatenate multiple audio files into one."""
    if len(audio_paths) == 1:
        # Just copy
        import shutil
        shutil.copy2(audio_paths[0], output_path)
        return True
    
    # Create concat file
    concat_file = output_path + ".txt"
    with open(concat_file, "w") as f:
        for path in audio_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        os.unlink(concat_file)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    if not check_ffmpeg():
        print("[ERROR] FFmpeg not found. Install from https://ffmpeg.org/download.html")
        print("        Or: winget install ffmpeg")
        sys.exit(1)
    
    os.makedirs(FINAL_DIR, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)
    
    print(f"\n{'='*50}")
    print(f"  FilterMate Video Assembler")
    print(f"  {len(SEQUENCE_MAP)} sequences to assemble")
    print(f"{'='*50}\n")
    
    # Check what we have
    has_diagrams = os.path.exists(DIAGRAMS_DIR) and len(os.listdir(DIAGRAMS_DIR)) > 0
    has_narration = os.path.exists(NARRATION_DIR)
    
    if not has_diagrams:
        print("[WARNING] No PNG diagrams found. Run generate_diagrams_standalone.py first.")
        print("          Will create title-card-only video.\n")
    
    clip_paths = []
    total_duration = 0.0
    
    for seq in SEQUENCE_MAP:
        seq_id = seq["id"]
        print(f"  [{seq_id}] {seq['title']}")
        
        clip_path = os.path.join(CLIPS_DIR, f"{seq_id}.mp4")
        
        # Find diagram
        diagram_path = None
        if has_diagrams and seq["diagrams"]:
            first_diagram = seq["diagrams"][0]
            candidate = os.path.join(DIAGRAMS_DIR, f"{first_diagram}.png")
            if os.path.exists(candidate):
                diagram_path = candidate
        
        # Find/concat narration
        audio_path = None
        if has_narration and seq["narrations"]:
            audio_files = []
            for nar_name in seq["narrations"]:
                candidate = os.path.join(NARRATION_DIR, f"{nar_name}.mp3")
                if os.path.exists(candidate):
                    audio_files.append(candidate)
            
            if len(audio_files) == 1:
                audio_path = audio_files[0]
            elif len(audio_files) > 1:
                audio_path = os.path.join(CLIPS_DIR, f"{seq_id}_narration.aac")
                concat_audio_files(audio_files, audio_path)
        
        # Create clip
        success = False
        if diagram_path:
            success = create_clip_from_diagram(
                diagram_path, audio_path, clip_path,
                duration=seq["fallback_duration"]
            )
        
        if not success:
            # Fallback: title card
            dur = seq["fallback_duration"]
            if audio_path:
                dur = get_audio_duration(audio_path) + 1.5
            success = create_title_card(seq["title"], clip_path, duration=dur)
        
        if success and os.path.exists(clip_path):
            clip_dur = get_audio_duration(clip_path) or seq["fallback_duration"]
            total_duration += clip_dur
            clip_paths.append(clip_path)
            print(f"    ✓ {clip_path} ({clip_dur:.1f}s)")
        else:
            print(f"    ✗ Failed to create clip")
    
    if not clip_paths:
        print("\n  [ERROR] No clips created. Cannot assemble video.")
        return
    
    # Concatenate all clips
    print(f"\n  Concatenating {len(clip_paths)} clips...")
    final_path = os.path.join(FINAL_DIR, "filtermate_presentation.mp4")
    concat_file = os.path.join(CLIPS_DIR, "concat_list.txt")
    
    with open(concat_file, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        final_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        final_duration = get_audio_duration(final_path) or total_duration
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        
        print(f"\n  ✅ Final video: {final_path}")
        print(f"     Duration: {final_duration:.0f}s ({final_duration/60:.1f} min)")
        print(f"     Size: {file_size:.1f} MB")
        print()
    except subprocess.CalledProcessError as e:
        print(f"\n  [ERROR] Final concat failed: {e.stderr.decode()[:300]}")


if __name__ == "__main__":
    main()
