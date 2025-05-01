# [CASCADE TEST LOG - ROOT] Top of nfo_backend.py loaded at runtime
import sys
print(f"[CASCADE TEST LOG - ROOT] Running script: {__file__} from {sys.argv}")
import os
import re
import datetime
from musicbrainz_search import search_musicbrainz_release, search_release_by_catno, get_release_by_id
print(f"[DEBUG] Running nfo_backend.py from: {os.path.abspath(__file__)} at {datetime.datetime.now()}")
import os
from mutagen.flac import FLAC
from discogs2nfo_batch import extract_track_titles, search_discogs_release, rename_to_discogs_release, sanitize_filename
import traceback
import binascii
import shutil
import json
from freedb_search import search_freedb_release
import sys

def get_template_path():
    # Try to load from settings file first
    settings_path = os.path.expanduser("~/.ripzbuddy_settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        if 'template_path' in settings and os.path.exists(settings['template_path']):
            return settings['template_path']
    # Prompt user for template path if not found
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "CDs.json")
    if os.path.exists(desktop_path):
        print(f"[DEBUG] Using template from desktop: {desktop_path}")
        return desktop_path
    print("[ERROR] No template file found. Please place your template (e.g. CDs.json) on your Desktop or set the template_path in settings.")
    sys.exit(1)

TEMPLATE_PATH = get_template_path()
print(f"[DEBUG] Loaded template: {TEMPLATE_PATH}")

# --- import token util ---
from discogs_token_util import load_discogs_token_from_template

def search_discogs_and_musicbrainz(artist, album):
    """
    Search Discogs and MusicBrainz for the given artist and album.
    Returns a list of matches suitable for GUI selection dialog.
    """
    from discogs2nfo_batch import search_discogs_release
    from musicbrainz_search import search_musicbrainz_release
    matches = []
    # Discogs search
    try:
        discogs_result = search_discogs_release([], f"{artist} {album}", None, return_first=False)
        if discogs_result:
            if isinstance(discogs_result, list):
                for rel in discogs_result:
                    matches.append({
                        "artist": rel.artists[0].name if getattr(rel, 'artists', None) and len(rel.artists) > 0 else 'Unknown',
                        "album": getattr(rel, 'title', 'Unknown'),
                        "year": getattr(rel, 'year', 'Unknown'),
                        "tracks": [t.title for t in getattr(rel, 'tracklist', [])],
                        "id": getattr(rel, 'id', None),
                        "source": "Discogs",
                        "release_obj": rel
                    })
            else:
                rel = discogs_result
                matches.append({
                    "artist": rel.artists[0].name if getattr(rel, 'artists', None) and len(rel.artists) > 0 else 'Unknown',
                    "album": getattr(rel, 'title', 'Unknown'),
                    "year": getattr(rel, 'year', 'Unknown'),
                    "tracks": [t.title for t in getattr(rel, 'tracklist', [])],
                    "id": getattr(rel, 'id', None),
                    "source": "Discogs",
                    "release_obj": rel
                })
    except Exception as e:
        print(f"[DEBUG] Discogs search failed: {e}")
    # MusicBrainz search
    try:
        mb_results = search_musicbrainz_release(artist, album)
        for mb_obj in mb_results:
            matches.append({
                "artist": getattr(mb_obj, 'artist', None) or (mb_obj.artist_credit[0]['artist']['name'] if hasattr(mb_obj, 'artist_credit') and mb_obj.artist_credit else 'Unknown'),
                "album": getattr(mb_obj, 'album', None) or getattr(mb_obj, 'title', 'Unknown'),
                "year": str(getattr(mb_obj, 'year', getattr(mb_obj, 'date', 'Unknown'))),
                "tracks": getattr(mb_obj, 'tracks', []) or [t['title'] for t in getattr(mb_obj, 'tracklist', [])] if hasattr(mb_obj, 'tracklist') else [],
                "id": getattr(mb_obj, 'id', None),
                "source": "MusicBrainz",
                "release_obj": mb_obj
            })
    except Exception as e:
        print(f"[DEBUG] MusicBrainz search failed: {e}")
    return matches

def robust_readlines(path):
    for enc in ('utf-8', 'cp1252', 'latin1'):
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not decode {path} as utf-8, cp1252, or latin1")

def safe_update_cue(cue_path, flac_filenames=None):
    import os
    import tempfile
    encodings = ['utf-8', 'cp1252', 'latin1']
    for enc in encodings:
        try:
            with open(cue_path, encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"Could not decode {cue_path}")
        return False

    directory = os.path.dirname(cue_path)
    if flac_filenames is None:
        flac_filenames = sorted([f for f in os.listdir(directory) if f.lower().endswith('.flac')])
    file_line_indices = [i for i, line in enumerate(lines) if line.strip().upper().startswith('FILE')]
    if len(file_line_indices) != len(flac_filenames):
        print("Mismatch between FILE lines and FLAC files. No changes made.")
        return False

    new_lines = list(lines)
    for idx, flac in zip(file_line_indices, flac_filenames):
        file_type = lines[idx].split()[-1] if len(lines[idx].split()) > 2 else 'WAVE'
        new_lines[idx] = f'FILE "{flac}" {file_type}\n'

    fd, tmp_path = tempfile.mkstemp(suffix='.cue.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding=enc) as f:
            f.writelines(new_lines)
        shutil.move(tmp_path, cue_path)
        print(f"Updated {cue_path} in place (safe, no .bak created!)")
        return True
    except Exception as e:
        print(f"[CRITICAL] Failed to update CUE file: {cue_path}. Error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False

def update_cue_in_place(cue_path):
    import os
    encodings = ['utf-8', 'cp1252', 'latin1']
    for enc in encodings:
        try:
            with open(cue_path, encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        print(f"Could not decode {cue_path}")
        return False

    directory = os.path.dirname(cue_path)
    flac_files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.flac')])
    file_line_indices = [i for i, line in enumerate(lines) if line.strip().upper().startswith('FILE')]
    if len(file_line_indices) != len(flac_files):
        print("Mismatch between FILE lines and FLAC files. No changes made.")
        return False

    for idx, flac in zip(file_line_indices, flac_files):
        file_type = lines[idx].split()[-1] if len(lines[idx].split()) > 2 else 'WAVE'
        lines[idx] = f'FILE "{flac}" {file_type}\n'

    with open(cue_path, 'w', encoding=enc) as f:
        f.writelines(lines)
    print(f"Updated {cue_path} in place (NO .bak created!)")
    return True

def sync_flacs_with_cue(album_path, cue_name=None, log_callback=print):
    import glob
    import os
    cue_files = glob.glob(os.path.join(album_path, '*.cue'))
    if cue_name:
        cue_files = [os.path.join(album_path, cue_name)] if os.path.exists(os.path.join(album_path, cue_name)) else cue_files
    if not cue_files:
        log_callback(f"[WARN] No CUE file found in {album_path}")
        return
    cue_path = cue_files[0]
    flac_files = sorted([f for f in os.listdir(album_path) if f.lower().endswith('.flac')])
    safe_update_cue(cue_path, flac_files)
    log_callback(f"[OK] Wrote sanitized CUE file as UTF-8 (CRLF): {cue_path}")

def write_cue_file(cue_path, cue_lines, log_callback=None):
    # Replace / with - in titles, enforce CRLF endings
    sanitized_lines = []
    for line in cue_lines:
        if line.strip().startswith('TITLE '):
            # Sanitize title line
            parts = line.split('TITLE ', 1)
            if len(parts) == 2:
                title = parts[1].strip().strip('"')
                title = title.replace('/', '-')
                sanitized_line = f'{parts[0]}TITLE "{title}"\r\n'
                sanitized_lines.append(sanitized_line)
                continue
        sanitized_lines.append(line.rstrip('\r\n') + '\r\n')
    with open(cue_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(sanitized_lines)
    if log_callback:
        log_callback(f"[OK] Wrote sanitized CUE file as UTF-8 (CRLF): {cue_path}")

def safe_join_path(directory, base_name, ext, max_path=259):
    import re
    # Replace Unicode dashes with ASCII dash
    base_name = re.sub(r'[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]', '-', base_name)
    # Remove forbidden characters
    base_name = re.sub(r'[\\/:*?"<>|]', '', base_name)
    # Remove non-ASCII characters
    base_name = re.sub(r'[^\x00-\x7F]', '', base_name)
    # Remove extra whitespace and colons
    base_name = base_name.replace(':', '').strip()
    # Collapse multiple spaces/underscores/dashes
    base_name = re.sub(r'[\s\-_]+', '_', base_name)
    # Truncate if path is too long
    full_path = os.path.join(directory, f"{base_name}{ext}")
    if len(full_path) > max_path:
        excess = len(full_path) - max_path
        base_name = base_name[:-excess]
        full_path = os.path.join(directory, f"{base_name}{ext}")
    return full_path

def get_release_base_name(discogs_release, flac_tags, max_length=40):
    """
    Generate a base name for output files. For albums with long/verbose names, keep only artist and main album (e.g., 'White_Zombie-Astro_Creep_2000'), removing everything after the first bracket, colon, or known verbose phrase.
    """
    import re
    # Discogs detection
    albumartist = ''
    if discogs_release:
        if hasattr(discogs_release, 'artists') and len(discogs_release.artists) > 0:
            albumartist = discogs_release.artists[0].name.strip().replace(' ', '_')
        elif hasattr(discogs_release, 'artist'):
            albumartist = getattr(discogs_release, 'artist', '').strip().replace(' ', '_')
    # FLAC fallback
    if not albumartist and flac_tags:
        albumartist = flac_tags.get('albumartist', [''])[0].strip().replace(' ', '_')
    # Robust VA detection
    va_aliases = {'various artists', 'va', 'various', 'v.a.', 'v.a', 'various-artists', 'various_artists'}
    normalized_albumartist = albumartist.lower().replace('-', ' ').replace('_', ' ').replace('.', '').strip()
    is_va = normalized_albumartist in va_aliases
    # Album/artist/year
    if discogs_release:
        album_title = getattr(discogs_release, 'title', 'Unknown Album')
        year = str(getattr(discogs_release, 'year', 'Unknown Year'))
        artist_name = albumartist if not is_va else ''
    else:
        album_title = flac_tags.get('album', ['Unknown Album'])[0]
        year = flac_tags.get('date', ['Unknown Year'])[0]
        artist_name = flac_tags.get('artist', ['Unknown Artist'])[0].replace(' ', '_')
    # Remove known verbose phrases and everything after first bracket/colon
    VERBOSE_PHRASES = [
        'Songs Of Love, Destruction And Other Synthetic Delusions Of The Electric Head',
        'Songs_Of_Love_Destruction_And_Other_Synthetic_Delusions_Of_The_Electric_Head',
        # Add more phrases as needed
    ]
    for phrase in VERBOSE_PHRASES:
        album_title = album_title.split(phrase)[0]
    # Remove everything after first bracket or colon
    album_title = re.split(r'[\(:\[]', album_title)[0].strip()
    # Replace spaces with underscores
    album_title = album_title.replace(' ', '_')
    # Truncate album_title to max_length minus artist/year/tags
    base_album = album_title[:max_length]
    if is_va:
        base = f"VA_-_{base_album}-FLAC-[{year}]-TSH"
    else:
        base = f"{artist_name}-{base_album}-FLAC-[{year}]-TSH"
    # Clean up filename
    base = re.sub(r'[\\/:*?"<>|]', '', base)
    base = re.sub(r'__+', '_', base)
    return base

def process_single_folder(album_path, template_json=None, discogs_client=None, log_callback=print):
    log_callback(f"[CASCADE TEST LOG - FUNC] Entered process_single_folder for: {album_path}")
    import binascii
    orig_album_path = album_path
    if not isinstance(album_path, (str, bytes, os.PathLike)):
        log_callback(f"[CRITICAL] album_path must be a path, not {type(album_path).__name__}. Skipping.")
        return
    # --- BEGIN: Early folder rename logic ---
    # Calculate intended new folder name before any file operations
    flac_tags = {}
    if os.listdir(album_path):
        try:
            from mutagen.flac import FLAC
            audio = FLAC(os.path.join(album_path, [f for f in os.listdir(album_path) if f.lower().endswith('.flac')][0]))
            for key in audio.keys():
                flac_tags[key] = audio[key]
        except Exception as e:
            log_callback(f"[WARN] Could not read FLAC tags: {e}")
    discogs_release = None
    id_tsh_path = os.path.join(album_path, 'id.tsh')
    if os.path.exists(id_tsh_path) and discogs_client:
        with open(id_tsh_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
            for line in lines:
                if 'discogs.com/release/' in line:
                    discogs_id = line.split('release/')[-1].split('-')[0]
                    try:
                        discogs_release = discogs_client.release(discogs_id)
                        log_callback(f"[OK] Loaded Discogs release by ID: {discogs_id} (title: {getattr(discogs_release, 'title', 'Unknown')})")
                    except Exception as e:
                        log_callback(f"[ERROR] Could not load Discogs release {discogs_id}: {e}")
    base_name = get_release_base_name(discogs_release, flac_tags)
    parent_dir = os.path.dirname(album_path)
    new_album_path = os.path.join(parent_dir, base_name)
    log_callback(f"[DEBUG] (EARLY) Folder rename check: album_path='{album_path}', base_name='{base_name}', new_album_path='{new_album_path}'")
    if os.path.abspath(album_path) != os.path.abspath(new_album_path):
        log_callback(f"[DEBUG] (EARLY) Attempting folder rename: '{album_path}' -> '{new_album_path}'")
        try:
            if not os.path.exists(new_album_path):
                os.rename(album_path, new_album_path)
                log_callback(f"[OK] Renamed folder: {album_path} -> {new_album_path}")
                album_path = new_album_path
            else:
                log_callback(f"[WARN] Target folder already exists: {new_album_path}")
                album_path = new_album_path
        except Exception as e:
            log_callback(f"[ERROR] Failed to rename folder: {e}")
    # --- END: Early folder rename logic ---
    # Now continue with all other processing using the (possibly updated) album_path
    # --- Always sanitize folder before any further processing ---
    album_path = shorten_dir_if_needed(album_path, log_callback=log_callback)
    flacs = [f for f in os.listdir(album_path) if f.lower().endswith('.flac')]
    if not flacs:
        log_callback(f"[SKIP] No FLACs found in {album_path}")
        return
    # Load template if not provided
    if template_json is None:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_json = json.load(f)
    # --- Fix: Always initialize discogs_client if not passed ---
    if discogs_client is None:
        try:
            import discogs_client
            from discogs_token_util import load_discogs_token_from_template
            token = load_discogs_token_from_template(template_json)
            discogs_client = discogs_client.Client('RipzBuddy/1.0', user_token=token)
            log_callback("[OK] Discogs client initialized.")
        except Exception as e:
            log_callback(f"[ERROR] Could not initialize Discogs client: {e}")
            discogs_client = None
    # Load Discogs release from id.tsh or other mechanism
    discogs_release = None
    id_tsh_path = os.path.join(album_path, 'id.tsh')
    if os.path.exists(id_tsh_path) and discogs_client:
        with open(id_tsh_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
            for line in lines:
                if 'discogs.com/release/' in line:
                    discogs_id = line.split('release/')[-1].split('-')[0]
                    try:
                        discogs_release = discogs_client.release(discogs_id)
                        log_callback(f"[OK] Loaded Discogs release by ID: {discogs_id} (title: {getattr(discogs_release, 'title', 'Unknown')})")
                    except Exception as e:
                        log_callback(f"[ERROR] Could not load Discogs release {discogs_id}: {e}")
    # --- Gather Discogs/FLAC info and set base_name ONCE ---
    flac_tags = {}
    if flacs:
        try:
            from mutagen.flac import FLAC
            audio = FLAC(os.path.join(album_path, flacs[0]))
            for key in audio.keys():
                flac_tags[key] = audio[key]
        except Exception as e:
            log_callback(f"[WARN] Could not read FLAC tags: {e}")

    # Always get base_name from Discogs/FLAC info
    base_name = get_release_base_name(discogs_release, flac_tags)
    parent_dir = os.path.dirname(album_path)
    new_album_path = os.path.join(parent_dir, base_name)
    log_callback(f"[DEBUG] Folder rename check: album_path='{album_path}', base_name='{base_name}', new_album_path='{new_album_path}'")

    # --- Rename folder if needed ---
    if os.path.abspath(album_path) != os.path.abspath(new_album_path):
        log_callback(f"[DEBUG] Attempting folder rename: '{album_path}' -> '{new_album_path}'")
        try:
            if not os.path.exists(new_album_path):
                os.rename(album_path, new_album_path)
                log_callback(f"[OK] Renamed folder: {album_path} -> {new_album_path}")
                album_path = new_album_path
            else:
                log_callback(f"[WARN] Target folder already exists: {new_album_path}")
                album_path = new_album_path
        except Exception as e:
            log_callback(f"[ERROR] Failed to rename folder: {e}")

    # --- Rename all created files to match base_name ---
    cue_files = [f for f in os.listdir(album_path) if f.lower().endswith('.cue')]
    # Only rename cues if there is exactly one cue file
    for ext in [".nfo", ".log", ".sfv", ".m3u"]:
        for f in os.listdir(album_path):
            if f.lower().endswith(ext):
                old_path = os.path.join(album_path, f)
                new_path = os.path.join(album_path, base_name + ext)
                if old_path != new_path:
                    try:
                        os.rename(old_path, new_path)
                        log_callback(f"[OK] Renamed {old_path} -> {new_path}")
                    except Exception as e:
                        log_callback(f"[ERROR] Failed to rename {old_path} -> {new_path}: {e}")
    # Only rename cue if there is exactly one cue file
    if len(cue_files) == 1:
        f = cue_files[0]
        old_path = os.path.join(album_path, f)
        new_path = os.path.join(album_path, base_name + ".cue")
        if old_path != new_path:
            try:
                os.rename(old_path, new_path)
                log_callback(f"[OK] Renamed {old_path} -> {new_path}")
            except Exception as e:
                log_callback(f"[ERROR] Failed to rename {old_path} -> {new_path}: {e}")

    # --- All further file writes use the new base_name and album_path ---
    # ... rest of the function remains unchanged ...

    # Preventative type check for album_path argument
    if not isinstance(album_path, (str, bytes, os.PathLike)):
        log_callback(f"[CRITICAL] album_path must be a path, not {type(album_path).__name__}. Skipping.")
        return
    flacs = [f for f in os.listdir(album_path) if f.lower().endswith('.flac')]
    if not flacs:
        log_callback(f"[SKIP] No FLACs found in {album_path}")
        return
    # Load template if not provided
    if template_json is None:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_json = json.load(f)
    # --- Fix: Always initialize discogs_client if not passed ---
    if discogs_client is None:
        try:
            import discogs_client
            from discogs_token_util import load_discogs_token_from_template
            token = load_discogs_token_from_template(template_json)
            discogs_client = discogs_client.Client('RipzBuddy/1.0', user_token=token)
            log_callback("[OK] Discogs client initialized.")
        except Exception as e:
            log_callback(f"[ERROR] Could not initialize Discogs client: {e}")
            discogs_client = None
    # Load Discogs release from id.tsh or other mechanism
    discogs_release = None
    id_tsh_path = os.path.join(album_path, 'id.tsh')
    if os.path.exists(id_tsh_path) and discogs_client:
        with open(id_tsh_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
            for line in lines:
                if 'discogs.com/release/' in line:
                    discogs_id = line.split('release/')[-1].split('-')[0]
                    try:
                        discogs_release = discogs_client.release(discogs_id)
                        log_callback(f"[OK] Loaded Discogs release by ID: {discogs_id} (title: {getattr(discogs_release, 'title', 'Unknown')})")
                    except Exception as e:
                        log_callback(f"[ERROR] Could not load Discogs release {discogs_id}: {e}")
    # --- RENAMING LOGIC: Rename FLACs and folder using Discogs data and template fields ---
    if discogs_release:
        try:
            from discogs2nfo_batch import rename_to_discogs_release
            new_album_path = rename_to_discogs_release(album_path, discogs_release, template_json=template_json)
            log_callback(f"[OK] Renamed files and folder using Discogs release data.")
            # Update album_path and flacs after renaming
            album_path = new_album_path
            flacs = [f for f in os.listdir(album_path) if f.lower().endswith('.flac')]
        except Exception as e:
            log_callback(f"[WARN] Failed to rename files/folder: {e}")
    # --- PREVENTATIVE ACTION: Ensure all renaming is complete before generating SFV/M3U ---
    # Remove any accidental pre-existing SFV/M3U files in the folder to prevent confusion
    for ext in ['.sfv', '.m3u']:
        pre_existing = os.path.join(album_path, base_name + ext)
        if os.path.exists(pre_existing):
            try:
                os.remove(pre_existing)
                log_callback(f"[DEBUG] Removed pre-existing {pre_existing} before regeneration.")
            except Exception as e:
                log_callback(f"[WARN] Could not remove pre-existing {pre_existing}: {e}")
    # After all FLAC renaming is complete, refresh the FLAC list
    flacs = [f for f in os.listdir(album_path) if f.lower().endswith('.flac')]
    log_callback(f"[DEBUG] Refreshed FLAC list before writing M3U/SFV: {flacs}")
    log_callback(f"[DEBUG] album_path at M3U/SFV write: {album_path}")
    log_callback(f"[DEBUG] os.listdir(album_path): {os.listdir(album_path)}")
    # Preventative: If flacs is empty, abort and log a clear error
    if not flacs:
        log_callback(f"[FATAL] No FLACs found in {album_path} at M3U/SFV write. Aborting file generation to prevent empty files.")
        return
    # --- M3U/SFV GENERATION (ensure always runs after FLAC/CUE/NFO) ---
    try:
        base_name = None
        for f in os.listdir(album_path):
            if f.lower().endswith('.nfo'):
                base_name = os.path.splitext(f)[0]
                break
        if not base_name:
            base_name = os.path.basename(album_path)
        if flacs:
            generate_m3u_and_sfv(album_path, flacs, base_name, log_callback)
        else:
            log_callback(f"[WARN] No FLAC files found for M3U/SFV generation in {album_path}")
    except Exception as e:
        log_callback(f"[ERROR] Exception in M3U/SFV generation: {e}")

    # ... rest of the code remains the same ...

MAX_PATH = 259  # Windows path limit

def shorten_dir_if_needed(dir_path, max_path=MAX_PATH, log_callback=print):
    import re
    import unicodedata
    parent, folder = os.path.split(dir_path)
    orig_dir_path = dir_path
    # --- Always sanitize folder name, not just if too long ---
    # Unicode normalization
    folder = unicodedata.normalize('NFKD', folder)
    # Replace all Unicode dashes/hyphens with ASCII dash
    folder = re.sub(r'[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D\u2013\u2014\u2015\u2012\u2011\u2043\u002d]', '-', folder)
    # Remove forbidden characters for Windows directories
    forbidden_chars = r'[\\/:*?"<>|]'
    short_folder = re.sub(forbidden_chars, '', folder)
    # Remove colons
    short_folder = short_folder.replace(':', '')
    # Remove commas
    short_folder = short_folder.replace(',', '')
    # Collapse whitespace, underscores, dashes
    short_folder = re.sub(r'[\s\-_]+', '_', short_folder)
    # Remove bracketed/parenthetical sections
    short_folder = re.sub(r'\s*\([^)]*\)', '', short_folder)
    short_folder = re.sub(r'\s*\[[^\]]*\]', '', short_folder)
    # Remove leading/trailing underscores
    short_folder = short_folder.strip('_')
    # Remove any remaining non-ASCII or control characters
    short_folder = ''.join(c for c in short_folder if 32 <= ord(c) <= 126)
    # Truncate if still too long
    while len(os.path.join(parent, short_folder)) > max_path and len(short_folder) > 10:
        short_folder = short_folder[:-1]
    new_dir_path = os.path.join(parent, short_folder)
    if new_dir_path != orig_dir_path:
        try:
            os.rename(orig_dir_path, new_dir_path)
            log_callback(f"[INFO] Renamed directory to avoid long path and sanitize: {orig_dir_path} -> {new_dir_path}")
        except Exception as e:
            log_callback(f"[ERROR] Failed to rename folder: {e}")
            return orig_dir_path
    return new_dir_path

def process_albums_gui(root_dir, template_json, log_callback=None, discogs_client=None, cd_mode=False):
    """
    Processes all album folders in root_dir (or the folder itself if it contains FLACs) and generates NFO files with Discogs metadata and renaming.
    """
    if log_callback is None:
        def gui_log_callback(msg):
            print(msg)
    else:
        gui_log_callback = log_callback

    log_file_path = os.path.join(root_dir, 'nfo_batch_log.txt')
    def file_log_callback(msg):
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            with open(log_file_path, 'a', encoding='utf-8') as logf:
                logf.write(msg + '\n')
        except Exception as e:
            print(f"[ERROR] Could not write to log file: {e}")

    def combined_log_callback(msg):
        file_log_callback(msg)
        if gui_log_callback:
            gui_log_callback(msg)

    def log_exception(context, exc):
        tb = traceback.format_exc()
        file_log_callback(f"[ERROR] {context}: {exc}\n{tb}")

    # Determine if batch or single
    try:
        log_callback(f"Listing directory: {root_dir}")
        entries = os.listdir(root_dir)
        has_subfolders = any(os.path.isdir(os.path.join(root_dir, entry)) for entry in entries)
        log_callback(f"Detected subfolders: {has_subfolders}")
        if has_subfolders:
            # Batch processing: always process ALL subfolders, regardless of name
            try:
                log_callback(f"Listing directory: {root_dir}")
                entries = os.listdir(root_dir)
                has_subfolders = any(os.path.isdir(os.path.join(root_dir, entry)) for entry in entries)
                log_callback(f"Detected subfolders: {has_subfolders}")
                if has_subfolders:
                    subfolders = [f for f in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, f))]
                    for folder_name in subfolders:
                        album_path = os.path.join(root_dir, folder_name)
                        if not os.path.exists(album_path):
                            continue
                        # --- Auto-shorten directory name if needed ---
                        album_path = shorten_dir_if_needed(album_path, log_callback=log_callback)
                        log_callback(f"[DEBUG] About to process: {album_path}")
                        process_single_folder(album_path, template_json=template_json, discogs_client=discogs_client, log_callback=log_callback)
                        log_callback(f"[DEBUG] Finished processing: {album_path}")
            except Exception as e:
                log_callback(f"[ERROR] Batch processing failed: {e}\n{traceback.format_exc()}")
        else:
            # Single mode: process the current folder
            log_callback(f"Single mode processing: {root_dir}")
            process_single_folder(root_dir, template_json=template_json, discogs_client=discogs_client, log_callback=log_callback)
        log_callback("All albums processed.")
    except Exception as e:
        log_exception("Exception in batch/single detection or processing", e)

def generate_m3u_and_sfv(album_path, flacs, base_name, log_callback=print):
    """
    Generate M3U playlist and SFV checksum file for the given album folder.
    """
    import hashlib
    import os
    # --- M3U ---
    m3u_path = os.path.join(album_path, base_name + '.m3u')
    try:
        with open(m3u_path, 'w', encoding='utf-8') as m3u_file:
            m3u_file.write("#EXTM3U\n")
            for flac in flacs:
                m3u_file.write(flac + "\n")
        log_callback(f"[OK] M3U written: {m3u_path}")
    except Exception as e:
        log_callback(f"[ERROR] Failed to write M3U: {e}")
    # --- SFV ---
    sfv_path = os.path.join(album_path, base_name + '.sfv')
    try:
        with open(sfv_path, 'w', encoding='utf-8') as sfv_file:
            for flac in flacs:
                file_path = os.path.join(album_path, flac)
                # Calculate CRC32
                buf_size = 65536
                crc = 0
                try:
                    with open(file_path, 'rb') as f:
                        while True:
                            data = f.read(buf_size)
                            if not data:
                                break
                            crc = binascii.crc32(data, crc)
                    crc = crc & 0xFFFFFFFF
                    sfv_file.write(f"{flac} {crc:08X}\n")
                except Exception as e:
                    log_callback(f"[ERROR] Failed to calculate CRC for {flac}: {e}")
        log_callback(f"[OK] SFV written: {sfv_path}")
    except Exception as e:
        log_callback(f"[ERROR] Failed to write SFV: {e}")