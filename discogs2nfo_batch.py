import re
# Copied from project root for GUI backend integration
import os
import shutil
import discogs_client
from mutagen.flac import FLAC
from datetime import datetime
import traceback
import hashlib
import zlib
from mutagen.flac import Picture

def sanitize_filename(text):
    text = re.sub(r'[\\/:*?"<>|]', '', text)
    text = text.replace(' ', '_')
    return text

def extract_track_titles(folder_path):
    # Preventative type check for folder_path
    if not isinstance(folder_path, (str, bytes, os.PathLike)):
        raise TypeError(f"extract_track_titles: folder_path must be a path string, not {type(folder_path).__name__}")
    if not os.path.exists(folder_path):
        print(f"[FATAL] extract_track_titles: folder does not exist: {folder_path}")
        return []
    titles = []
    for fname in sorted(os.listdir(folder_path)):
        if fname.lower().endswith('.flac'):
            audio = FLAC(os.path.join(folder_path, fname))
            titles.append(audio.get('title', [os.path.splitext(fname)[0]])[0])
    return titles

def clean_search_name(folder_name):
    # Remove common tags and patterns from folder names for Discogs search
    name = folder_name.lower()
    # Remove tags like -12-vinyl-tsh, -tsh, -12-vinyl, -vinyl, -flac, -web, -cd, -promo, -single, -ep, -lp, -wav, -mp3
    remove_patterns = [
        r'-\d{2}-vinyl-tsh', r'-vinyl-tsh', r'-\d{2}-vinyl', r'-vinyl', r'-tsh',
        r'-flac', r'-web', r'-cd', r'-promo', r'-single', r'-ep', r'-lp', r'-wav', r'-mp3'
    ]
    for pat in remove_patterns:
        name = re.sub(pat, '', name)
    # Remove extra dashes, underscores, and spaces
    name = re.sub(r'[-_]+', ' ', name)
    name = name.strip()
    return name

def normalize_artist(artist):
    va_terms = ["va", "v.a.", "various", "various artists", "various-artist"]
    if artist.strip().lower() in va_terms:
        return "Various"
    return artist.strip()

def clean_album_title(title):
    title = title.replace('_', ' ').replace('-', ' ').strip()
    title = re.sub(r'\s+', ' ', title)
    return title

def get_discogs_release_by_id(discogs_client, release_id):
    try:
        release = discogs_client.release(int(release_id))
        print(f"[Discogs] Directly fetched release {release_id}")
        return release
    except Exception as e:
        print(f"[Discogs] Failed to fetch release by id {release_id}: {e}")
        return None

def search_discogs_release(track_titles, folder_name, discogs_client, discogs_id=None, return_first=True):
    if discogs_id and discogs_client:
        release = get_discogs_release_by_id(discogs_client, discogs_id)
        if release:
            return release
    # Existing logic
    match = re.match(r"(.*?) - (.*?) - FLAC", folder_name) if folder_name else None
    if match:
        artist, album = match.groups()
    else:
        artist = "Various"
        album = folder_name or ''
    artist = normalize_artist(artist)
    album = clean_album_title(album)
    try:
        results = discogs_client.search(album, artist=artist, type='release')
        releases = list(results)
        if releases:
            print(f"[Discogs] Found {len(releases)} results for '{artist}' - '{album}'")
            return releases[0] if return_first else releases
    except Exception as e:
        print(f"[Discogs] Search error: {e}")
    try:
        results = discogs_client.search(album, artist="Various", type='release')
        releases = list(results)
        if releases:
            print(f"[Discogs] Fallback found {len(releases)} results for 'Various' - '{album}'")
            return releases[0] if return_first else releases
    except Exception as e:
        print(f"[Discogs] Fallback search error: {e}")
    print(f"[Discogs] No release found for '{artist}' - '{album}'")
    return None

def rename_to_discogs_release(folder_path, release, template_json=None, discogs_client=None):
    import unicodedata
    from nfo_backend import normalize_artist_folder
    parent_dir = os.path.dirname(folder_path)
    # Compose new folder name
    raw_artist = release.artists[0].name
    norm_artist = normalize_artist_folder(raw_artist)
    safe_artist = sanitize_filename(norm_artist)
    safe_album = sanitize_filename(release.title.replace('_', ' '))
    year = release.year if hasattr(release, 'year') and release.year else 'Unknown'
    # Extract template fields
    release_group = ''
    flac_tag = ''
    if template_json:
        release_group = template_json.get('release_group', '')
        flac_tag = template_json.get('format', 'FLAC')
        if not flac_tag:
            flac_tag = 'FLAC'
    # Add fields to folder name if present, always put release_group at the end
    # Format: VA - Album_-_Title-(Year)-[type of audio file]-[release group name]
    parts = [safe_artist, ' - ', safe_album, f'-({year})']
    if flac_tag:
        parts.append(f'-[{flac_tag}]')
    if release_group:
        parts.append(f'-[{release_group}]')
    new_folder_name = ''.join(parts)
    new_folder_path = os.path.join(parent_dir, new_folder_name)
    if os.path.abspath(folder_path) != os.path.abspath(new_folder_path):
        if not os.path.exists(new_folder_path):
            os.rename(folder_path, new_folder_path)
            print(f"Renamed folder to: {new_folder_name}")
            folder_path = new_folder_path
        else:
            print(f"Target folder {new_folder_name} already exists. Skipping folder rename.")
    flac_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.flac')]
    # --- Begin: Enforce flat, disc-aware numbering for multi-disc releases with full track info ---
    cue_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.cue')]
    disc_count = 1
    disc_map = {}
    for cue in cue_files:
        m = re.search(r'cd(\d+)', cue, re.IGNORECASE)
        if m:
            disc_num = int(m.group(1))
            disc_map[disc_num] = []
    if disc_map:
        disc_count = len(disc_map)
    # Build tracklist map: [(disc_num, track_num, artist, title, version)]
    tracks = []
    for track in release.tracklist:
        # Try to parse disc number from position (e.g. '2-01')
        disc_num, track_num = 1, 0
        if hasattr(track, 'position') and track.position:
            pos = track.position.replace(' ', '').replace('_', '-')
            m = re.match(r'(\d+)[-_.]?(\d+)', pos)
            if m:
                disc_num = int(m.group(1))
                track_num = int(m.group(2))
            else:
                track_num = int(pos) if pos.isdigit() else 0
        artist = getattr(track, 'artists', [release.artists[0]])[0].name if hasattr(track, 'artists') and track.artists else release.artists[0].name
        title = track.title if hasattr(track, 'title') else 'Unknown Title'
        # Extract version/remix from title if present
        version = ''
        version_m = re.search(r'\(([^)]+)\)', title)
        if version_m:
            version = version_m.group(1)
            title = title.replace(version_m.group(0), '').strip()
        tracks.append((disc_num, track_num, artist, title, version))
    # Sort tracks by disc and track
    tracks = sorted([t for t in tracks if t[1] > 0], key=lambda x: (x[0], x[1]))
    flac_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.flac')])
    if len(flac_files) != len(tracks):
        print(f"[WARN] FLAC count ({len(flac_files)}) != track count ({len(tracks)}), fallback to flat numbering.")
        # fallback: assign by order
        for idx, flac in enumerate(flac_files):
            disc_num = 1 + idx // 99
            track_num = 1 + idx % 99
            track = tracks[idx] if idx < len(tracks) else (disc_num, track_num, '', '', '')
            new_track_num = disc_num * 100 + track_num
            ext = os.path.splitext(flac)[1]
            name_parts = [f"{new_folder_name}-{new_track_num:03d}"]
            if track[2]:
                name_parts.append(f"- {track[2]}")
            if track[3]:
                name_parts.append(f" - {track[3]}")
            if track[4]:
                name_parts.append(f" ({track[4]})")
            new_name = ''.join(name_parts) + ext
            old_path = os.path.join(folder_path, flac)
            new_path = os.path.join(folder_path, new_name)
            if os.path.abspath(old_path) != os.path.abspath(new_path):
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"Renamed {flac} to {new_name}")
                else:
                    print(f"Target file {new_name} already exists. Skipping file rename.")
    else:
        for idx, (flac, track) in enumerate(zip(flac_files, tracks)):
            disc_num, track_num, artist, title, version = track
            new_track_num = disc_num * 100 + track_num
            ext = os.path.splitext(flac)[1]
            name_parts = [f"{new_folder_name}-{new_track_num:03d}"]
            if artist:
                name_parts.append(f" - {artist}")
            if title:
                name_parts.append(f" - {title}")
            if version:
                name_parts.append(f" ({version})")
            new_name = ''.join(name_parts) + ext
            old_path = os.path.join(folder_path, flac)
            new_path = os.path.join(folder_path, new_name)
            if os.path.abspath(old_path) != os.path.abspath(new_path):
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    print(f"Renamed {flac} to {new_name}")
                else:
                    print(f"Target file {new_name} already exists. Skipping file rename.")
    # --- End: Enforce flat, disc-aware numbering with full track info ---
    # --- Begin: Cleanup legacy files not matching new pattern ---
    import unicodedata
    backup_dir = os.path.join(folder_path, "backup_legacy_files")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    # Define the new naming pattern for this release
    pattern = re.compile(re.escape(new_folder_name) + r"-\d{3}.*\\.flac$", re.IGNORECASE)
    for f in os.listdir(folder_path):
        if f.lower().endswith('.flac') and not pattern.match(f):
            src = os.path.join(folder_path, f)
            dst = os.path.join(backup_dir, f)
            print(f"[CLEANUP] Moving legacy file {src} to {dst}")
            try:
                shutil.move(src, dst)
            except Exception as e:
                print(f"[ERROR] Could not move {src}: {e}")
    # --- End: Cleanup legacy files ---
    # --- Begin: Postflight summary ---
    print("[SUMMARY] Final FLAC files in folder:")
    for f in sorted(os.listdir(folder_path)):
        if f.lower().endswith('.flac'):
            print(f"  - {f}")
    print(f"[SUMMARY] Legacy files moved to: {backup_dir}")
    # --- End: Postflight summary ---
    return folder_path

# --- Robust error handling for batch processing ---
def safe_process_folder(process_fn, *args, **kwargs):
    try:
        result = process_fn(*args, **kwargs)
        # Check if folder exists after processing
        folder = args[0] if args else None
        if folder and not os.path.exists(folder):
            print(f"[FATAL] Folder missing after processing: {folder}. Aborting further steps for this album.")
            return None
        return result
    except Exception as e:
        print(f"[FATAL] Exception during processing: {e}")
        return None

def generate_m3u(track_files, folder_path, output_base):
    m3u_path = os.path.join(folder_path, f"{output_base}.m3u")
    print(f"[DEBUG] Entering M3U writing block for {folder_path}")
    try:
        with open(m3u_path, 'w', encoding='utf-8') as f:
            f.write("# TEST LINE: M3U file is writable\n")
            for track in track_files:
                abs_track = os.path.join(folder_path, track)
                print(f"[DEBUG] Writing M3U entry for: {abs_track}")
                try:
                    f.write(f"{track}\n")
                except Exception as e:
                    print(f"[ERROR] Failed to write M3U entry for {abs_track}: {e}")
        print(f"[OK] Generated M3U: {m3u_path}")
    except Exception as e:
        print(f"[ERROR] Failed to create/write M3U: {e}")
    print(f"[DEBUG] Exiting M3U writing block for {folder_path}")

def generate_sfv(track_files, folder_path, output_base):
    sfv_path = os.path.join(folder_path, f"{output_base}.sfv")
    print(f"[DEBUG] Entering SFV writing block for {folder_path}")
    try:
        with open(sfv_path, 'w', encoding='utf-8') as f:
            f.write("# TEST LINE: SFV file is writable\n")
            for track in track_files:
                abs_track = os.path.join(folder_path, track)
                print(f"[DEBUG] Writing SFV entry for: {abs_track}")
                try:
                    crc = 0
                    with open(abs_track, 'rb') as tf:
                        for chunk in iter(lambda: tf.read(4096), b''):
                            crc = zlib.crc32(chunk, crc)
                    f.write(f"{track} {crc & 0xFFFFFFFF:08X}\n")
                except Exception as e:
                    print(f"[ERROR] Failed to compute CRC for {abs_track}: {e}")
                    f.write(f"{track} ERROR\n")
        print(f"[OK] Generated SFV: {sfv_path}")
    except Exception as e:
        print(f"[ERROR] Failed to create/write SFV: {e}")
    print(f"[DEBUG] Exiting SFV writing block for {folder_path}")

def postprocess_album_folder(album_folder_path):
    print(f"[DEBUG] ENTER postprocess_album_folder: {album_folder_path}")
    dir_listing = os.listdir(album_folder_path)
    print(f"[DEBUG] Directory listing: {dir_listing}")
    base_name = None
    for f in dir_listing:
        if f.lower().endswith('.nfo'):
            base_name = os.path.splitext(f)[0]
            break
    if not base_name:
        base_name = os.path.basename(album_folder_path)
    flac_files = sorted([f for f in dir_listing if f.lower().endswith('.flac')])
    print(f"[DEBUG] FLAC files found for M3U/SFV: {flac_files}")
    if not flac_files:
        print(f"[WARN] No FLAC files found in {album_folder_path} at postprocessing time!")
    else:
        generate_m3u(flac_files, album_folder_path, base_name)
        generate_sfv(flac_files, album_folder_path, base_name)
    print(f"[DEBUG] EXIT postprocess_album_folder: {album_folder_path}")

ascii_header = r"""
... (ASCII art omitted for brevity) ...
"""

# === BEGIN: Use robust batch logic from nfo_backend.py ===
from nfo_backend import process_albums_gui
from robust_cue_renamer import robust_cue_renamer

def batch_log_callback(msg):
    print(msg)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Batch NFO/CUE generator for album folders.')
    parser.add_argument('root_dir', help='Root directory containing album subfolders')
    args = parser.parse_args()
    # Discogs API authentication using OAuth tokens
    d = discogs_client.Client(
        'TheSoundHouseNFOApp/1.0',
        consumer_key='dZcgvrZrDnbnbSKhbhtQ',
        consumer_secret='dxeWMPEkeIoDVjaUWtheKRkIqNvBSmsT'
    )
    process_albums_gui(
        args.root_dir,
        ascii_art='',
        ripper='',
        group='',
        equipment='',
        software='',
        presents_enabled=False,
        presents_group='',
        log_callback=batch_log_callback,
        discogs_client=d,
        cd_mode=False
    )
    # After processing, run robust cue renamer and post-process for every album folder
    from discogs2nfo_batch import safe_process_folder
    for album_folder in os.listdir(args.root_dir):
        full_album_path = os.path.join(args.root_dir, album_folder)
        if os.path.isdir(full_album_path):
            safe_process_folder(robust_cue_renamer, full_album_path)
            postprocess_album_folder(full_album_path)

# === END: Use robust batch logic from nfo_backend.py ===
