import os
import sys
from mutagen.flac import FLAC
import discogs_client
import re
from discogs_token_util import load_discogs_token_from_template

def extract_discogs_id_from_tsh(tsh_path):
    if not os.path.exists(tsh_path):
        return None
    with open(tsh_path, encoding='utf-8', errors='ignore') as f:
        content = f.read().strip()
    m = re.search(r'discogs.com/release/(\d+)', content)
    if m:
        return int(m.group(1))
    if content.isdigit():
        return int(content)
    return None

def update_flac_tags_with_discogs(flac_path, artist, title):
    try:
        audio = FLAC(flac_path)
        audio['artist'] = artist
        audio['title'] = title
        audio.save()
        print(f"[OK] Updated FLAC tags: {os.path.basename(flac_path)} -> {artist} - {title}")
    except Exception as e:
        print(f"[WARN] Could not update FLAC tags for {flac_path}: {e}")

def rewrite_cue_with_discogs(cue_path, flac_files, discogs_tracks):
    try:
        with open(cue_path, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        new_lines = []
        flac_idx = 0
        track_idx = 0
        for line in lines:
            if line.strip().upper().startswith('FILE') and flac_idx < len(flac_files):
                new_lines.append(f'FILE "{flac_files[flac_idx]}" WAVE\n')
                flac_idx += 1
            elif line.strip().upper().startswith('TITLE') and track_idx < len(discogs_tracks):
                new_lines.append(f'    TITLE "{discogs_tracks[track_idx][1]}"\n')
            elif line.strip().upper().startswith('PERFORMER') and track_idx < len(discogs_tracks):
                new_lines.append(f'    PERFORMER "{discogs_tracks[track_idx][0]}"\n')
                track_idx += 1
            else:
                new_lines.append(line)
        bak_path = cue_path + '.bak'
        os.replace(cue_path, bak_path)
        with open(cue_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"[OK] Rewrote cue file with Discogs data: {os.path.basename(cue_path)}")
    except Exception as e:
        print(f"[WARN] Could not rewrite cue {cue_path}: {e}")

def reconcile_folder(folder, discogs_client):
    cue_files = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
    flac_files = sorted([f for f in os.listdir(folder) if f.lower().endswith('.flac')])
    if not cue_files or not flac_files:
        print(f"[SKIP] No cue or FLACs in {folder}")
        return
    id_tsh = os.path.join(folder, 'id.tsh')
    discogs_id = extract_discogs_id_from_tsh(id_tsh)
    if not discogs_id:
        print(f"[SKIP] No Discogs release for {folder}")
        return
    try:
        release = discogs_client.release(discogs_id)
    except Exception as e:
        print(f"[SKIP] Could not fetch Discogs release {discogs_id}: {e}")
        return
    discogs_tracks = []
    for track in release.tracklist:
        artist = track.artists[0].name if hasattr(track, 'artists') and track.artists else (release.artists[0].name if hasattr(release, 'artists') and release.artists else 'Various')
        title = track.title
        discogs_tracks.append((artist, title))
    for idx, flac in enumerate(flac_files):
        if idx < len(discogs_tracks):
            update_flac_tags_with_discogs(os.path.join(folder, flac), discogs_tracks[idx][0], discogs_tracks[idx][1])
    for cue in cue_files:
        rewrite_cue_with_discogs(os.path.join(folder, cue), flac_files, discogs_tracks)

def main(root):
    token = load_discogs_token_from_template()
    discogs = discogs_client.Client('nfo-reconcile/1.0', user_token=token)
    for sub in os.listdir(root):
        folder = os.path.join(root, sub)
        if os.path.isdir(folder):
            reconcile_folder(folder, discogs)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python discogs_reconcile_batch.py <root_folder>")
    else:
        main(sys.argv[1])
