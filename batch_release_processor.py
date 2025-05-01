import os
import re
import shutil
from mutagen.flac import FLAC

def sanitize_filename(text):
    return re.sub(r'[\\/:*?"<>|]', '', text)

def get_release_base_name(artist, album, year, group):
    artist_part = artist.replace(' ', '_')
    album_part = album.replace(' ', '_')
    return f"{artist_part}-{album_part}-FLAC-[{year}]-{group}"

def update_cue_file(cue_path, flac_files):
    with open(cue_path, encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    flac_idx = 0
    for line in lines:
        if line.strip().upper().startswith('FILE'):
            if flac_idx < len(flac_files):
                new_file = flac_files[flac_idx]
                # Only update filename and extension
                new_lines.append(f'FILE "{new_file}" WAVE\n')
                flac_idx += 1
            else:
                continue
        else:
            # Replace .wav with .flac in FILE lines if needed
            new_lines.append(line.replace('.wav', '.flac'))
    # Add missing FILE lines if needed
    while flac_idx < len(flac_files):
        new_file = flac_files[flac_idx]
        new_lines.append(f'FILE "{new_file}" WAVE\n')
        flac_idx += 1
    shutil.copy2(cue_path, cue_path + '.bak')
    with open(cue_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"[OK] Updated cue: {cue_path}")

def generate_tracklist(flac_info, various=True):
    lines = []
    for (disc, track, artist, title, flac) in flac_info:
        if various:
            lines.append(f"  {disc*100+track:03d}. {artist} - {title}")
        else:
            lines.append(f"  {disc*100+track:03d}. {title}")
    return '\n'.join(lines)

def process_release(folder, nfo_template, group, presents, discogs_info, various=True):
    # Gather FLAC info
    flacs = sorted([f for f in os.listdir(folder) if f.lower().endswith('.flac')])
    flac_info = []
    year = None
    album = None
    artist = "VA" if various else None
    for flac in flacs:
        src_path = os.path.join(folder, flac)
        audio = FLAC(src_path)
        discnumber = int(audio.get('discnumber', [1])[0])
        tracknumber = int(audio.get('tracknumber', [1])[0])
        track_artist = audio.get('artist', ["Unknown Artist"])[0]
        title = audio.get('title', ["Unknown Title"])[0]
        if not year:
            year = audio.get('date', [None])[0]
        if not album:
            album = audio.get('album', [None])[0]
        if not artist and not various:
            artist = track_artist
        flac_info.append((discnumber, tracknumber, track_artist, title, flac))
    # Sort by disc and track
    flac_info.sort()
    # Naming logic
    base_name = get_release_base_name(artist, album, year, group)
    # Rename FLACs
    correct_names = []
    for disc, track, track_artist, title, flac in flac_info:
        ext = os.path.splitext(flac)[1]
        final_track_num = disc*100 + track
        new_flac = f"{final_track_num:03d} - {track_artist} - {title}{ext}" if various else f"{final_track_num:03d} - {title}{ext}"
        new_flac = sanitize_filename(new_flac)
        src = os.path.join(folder, flac)
        dst = os.path.join(folder, new_flac)
        correct_names.append(new_flac)
        if src != dst:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
            print(f"[OK] Renamed {src} -> {dst}")
    # Update CUE
    cues = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
    for cue in cues:
        cue_path = os.path.join(folder, cue)
        update_cue_file(cue_path, correct_names)
    # Rename/create NFO, M3U, SFV, LOG
    for ext in ['.nfo', '.m3u', '.sfv', '.log']:
        target = os.path.join(folder, base_name + ext)
        if ext == '.nfo':
            # Generate NFO from template
            tracklist = generate_tracklist(flac_info, various=various)
            nfo_content = nfo_template.replace('{TRACKLIST}', tracklist)
            nfo_content = nfo_content.replace('{DISCOGS}', discogs_info)
            nfo_content = nfo_content.replace('{GROUP}', group)
            nfo_content = nfo_content.replace('{PRESENTS}', presents)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            print(f"[OK] NFO written: {target}")
        else:
            # Rename or create empty file if not present
            files = [f for f in os.listdir(folder) if f.lower().endswith(ext)]
            for f in files:
                src = os.path.join(folder, f)
                if src != target:
                    if os.path.exists(target):
                        os.remove(target)
                    os.rename(src, target)
                    print(f"[OK] Renamed {src} -> {target}")
            if not files:
                open(target, 'a').close()
    print(f"[DONE] Release processed: {folder}")

# Example batch usage:
if __name__ == "__main__":
    import sys
    # Simulate GUI input
    # folders = [list of folders selected in GUI]
    # nfo_template = loaded template string from GUI
    # group = group name from GUI
    # presents = presents entry from GUI
    # discogs_info = discogs info from GUI
    # various = True if VA release, else False
    # For demo, just print usage
    print("This script is intended to be called from the GUI batch process with all required inputs.")
    print("process_release(folder, nfo_template, group, presents, discogs_info, various=True)")
