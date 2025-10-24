#!/usr/bin/env python3
import argparse
import zipfile
import tempfile
import shutil
import re
from pathlib import Path
from mutagen import File as MutagenFile


def extract_zip(zip_path, temp_dir):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)
    return Path(temp_dir)


def sanitize_name(name):
    """Remove special characters and extra spaces."""
    name = re.sub(r'[<>:"/\\|?*]', '', name or "")
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def get_metadata(audio_path):
    """Extract artist, album, track number, and title from metadata."""
    audio = MutagenFile(audio_path, easy=True)
    if not audio:
        return None, None, None, None

    artist = audio.get("artist", [None])[0]
    album = audio.get("album", [None])[0]
    title = audio.get("title", [None])[0]
    tracknumber = audio.get("tracknumber", [None])[0]

    if tracknumber and isinstance(tracknumber, str):
        tracknumber = tracknumber.split("/")[0].zfill(2)
    else:
        tracknumber = None

    return artist, album, tracknumber, title


def organize_files(temp_dir, output_dir):
    supported_audio = [".flac", ".mp3", ".m4a", ".wav"]

    for file in Path(temp_dir).rglob("*"):
        if file.is_dir():
            continue

        # Audio file organization
        if file.suffix.lower() in supported_audio:
            artist, album, tracknum, title = get_metadata(file)
            if not artist or not album:
                print(f"Skipping {file.name} (missing metadata)")
                continue

            artist = sanitize_name(artist)
            album = sanitize_name(album)
            dest_dir = Path(output_dir) / artist / album
            dest_dir.mkdir(parents=True, exist_ok=True)

            if tracknum and title:
                new_name = f"{tracknum} {sanitize_name(title)}{file.suffix}"
            elif title:
                new_name = f"{sanitize_name(title)}{file.suffix}"
            else:
                new_name = sanitize_name(file.name)

            dest_file = dest_dir / new_name
            # Avoid accidental overwrites
            if dest_file.exists():
                stem, ext = dest_file.stem, dest_file.suffix
                i = 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{stem}_{i}{ext}"
                    i += 1

            shutil.move(str(file), dest_file)
            print(f"→ {artist} / {album} / {dest_file.name}")

        # Cover image organization
        elif file.stem.lower() == "cover":
            for f in file.parent.iterdir():
                if f.suffix.lower() in supported_audio:
                    artist, album, *_ = get_metadata(f)
                    if artist and album:
                        artist = sanitize_name(artist)
                        album = sanitize_name(album)
                        dest_dir = Path(output_dir) / artist / album
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file), dest_dir / file.name)
                        print(f"✓ Moved cover to {artist}/{album}")
                        break


def main():
    parser = argparse.ArgumentParser(description="Extract and organize audio files by metadata.")
    parser.add_argument("--file", required=True, help="Path to ZIP file containing audio files.")
    parser.add_argument("--output", default="output", help="Destination root directory.")
    parser.add_argument("--remove", action="store_true", help="Delete the ZIP file after conversion.")
    args = parser.parse_args()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Extracting {args.file} ...")
            extract_zip(args.file, tmpdir)
            print("Organizing files ...")
            organize_files(tmpdir, args.output)
            print(f"✅ Done. Files saved under '{args.output}/'")

    finally:
        if args.remove and Path(args.file).exists():
            try:
                Path(args.file).unlink()
                print(f"🗑️ Removed input ZIP file: {args.file}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to remove {args.file}: {e}")


if __name__ == "__main__":
    main()

