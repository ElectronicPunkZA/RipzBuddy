import os
import re
import shutil
from mutagen.flac import FLAC

def get_base_name(folder):
    return os.path.basename(os.path.normpath(folder))

def update_cue_file(cue_path, flac_files, new_cue_path):
    with open(cue_path, encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    flac_idx = 0
    for line in lines:
        if line.strip().upper().startswith('FILE'):
            m = re.match(r'FILE\s+"(.+?)"\s+WAVE', line, re.IGNORECASE)
            if m and flac_idx < len(flac_files):
                # Replace .wav with .flac and set correct filename
                new_file = flac_files[flac_idx]
                new_lines.append(f'FILE "{new_file}" WAVE\n')
                flac_idx += 1
            else:
                # If more FLACs than FILE lines, add missing FILE lines
                if flac_idx < len(flac_files):
                    new_file = flac_files[flac_idx]
                    new_lines.append(f'FILE "{new_file}" WAVE\n')
                    flac_idx += 1
                else:
                    new_lines.append(line)
        else:
            new_lines.append(line)
    # If more FLACs than FILE lines, append FILE lines at the end
    while flac_idx < len(flac_files):
        new_file = flac_files[flac_idx]
        new_lines.append(f'FILE "{new_file}" WAVE\n')
        flac_idx += 1
    # Backup original
    shutil.copy2(cue_path, cue_path + '.bak')
    with open(new_cue_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"[OK] Updated cue written: {new_cue_path}")

def rename_metadata_files(folder, base_name):
    for ext in ['.nfo', '.sfv', '.m3u', '.log', '.cue']:
        files = [f for f in os.listdir(folder) if f.lower().endswith(ext)]
        for f in files:
            target = os.path.join(folder, base_name + ext)
            src = os.path.join(folder, f)
            if src != target:
                if os.path.exists(target):
                    print(f"[WARN] {target} already exists, skipping rename.")
                else:
                    os.rename(src, target)
                    print(f"[OK] Renamed {src} -> {target}")

def robust_cue_renamer(folder):
    if not os.path.exists(folder):
        print(f"[ERROR] Folder does not exist: {folder}")
        return
    cues = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
    if not cues:
        print("[WARN] No CUE files found.")
        return
    flacs = sorted([f for f in os.listdir(folder) if f.lower().endswith('.flac')])
    print(f"[INFO] Renaming all {len(flacs)} FLAC files in folder to <tracknumber> - <artist> - <title>.flac format.")
    def sanitize_filename(text):
        return re.sub(r'[\\/:*?\"<>|]', '', text)
    flac_info = []
    for idx, flac in enumerate(flacs):
        src_path = os.path.join(folder, flac)
        try:
            audio = FLAC(src_path)
            track_num = int(audio.get('tracknumber', [idx+1])[0])
            artist = audio.get('artist', ['Unknown Artist'])[0]
            title = audio.get('title', ['Unknown Title'])[0]
            version = audio.get('version', [''])[0]
            if version:
                title = f"{title} ({version})"
        except Exception as e:
            print(f"[WARN] Could not read tags for {flac}: {e}, using fallback order.")
            track_num = idx+1
            artist = 'Unknown Artist'
            title = 'Unknown Title'
        flac_info.append((track_num, artist, title, flac))
    # Sort by track number
    flac_info.sort()
    renamed = 0
    correct_names = []
    for track_num, artist, title, flac in flac_info:
        ext = os.path.splitext(flac)[1]
        new_flac = f"{track_num:02d} - {artist} - {title}{ext}"
        new_flac = sanitize_filename(new_flac)
        src = os.path.join(folder, flac)
        dst = os.path.join(folder, new_flac)
        correct_names.append(new_flac)
        if src != dst:
            if os.path.exists(dst):
                os.remove(dst)  # Overwrite if exists
            os.rename(src, dst)
            print(f"[OK] Renamed {src} -> {dst}")
        renamed += 1
    print(f"[SUMMARY] {renamed} FLACs renamed. Only correct files remain in the folder.")
    # --- CUE MISMATCH FIX LOGIC ---
    for cue in cues:
        cue_path = os.path.join(folder, cue)
        update_cue_file(cue_path, correct_names, cue_path)
    # Cleanup: remove any .flac files not matching the new pattern
    pattern = re.compile(r'^\d{2} - .+ - .+\.flac$', re.IGNORECASE)
    for f in os.listdir(folder):
        if f.lower().endswith('.flac') and not pattern.match(f):
            full_path = os.path.join(folder, f)
            if f not in correct_names:
                print(f"[CLEANUP] Deleting legacy file {full_path}")
                os.remove(full_path)
    # After renaming, update cue files to reference correct FLACs (already done above)
    rename_metadata_files(folder, os.path.basename(os.path.normpath(folder)))

if __name__ == "__main__":
    import sys
    import traceback
    try:
        if len(sys.argv) > 1:
            robust_cue_renamer(sys.argv[1])
        else:
            print("Usage: python robust_cue_renamer.py <folder>")
    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}\n{traceback.format_exc()}")
