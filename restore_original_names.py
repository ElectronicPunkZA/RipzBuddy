import os
import re
import shutil

# --- CONFIG ---
ROOT_DIR = r"F:/CD COLLECTION/TEST DIRECTORY"  # Update this to your collection root
BACKUP_CUE = True  # Set True to backup cues before editing


def find_cue_file(folder):
    for f in os.listdir(folder):
        if f.lower().endswith('.cue'):
            return os.path.join(folder, f)
    return None

def parse_cue_files(cue_path):
    """Returns a list of original FLAC filenames from the CUE file."""
    flac_files = []
    with open(cue_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r'\s*FILE\s+"([^"]+)"\s+WAVE', line)
            if m:
                flac_files.append(m.group(1))
    return flac_files

def get_current_flacs(folder):
    return sorted([f for f in os.listdir(folder) if f.lower().endswith('.flac')])

def rename_flacs_to_cue(folder):
    cue_files = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
    flac_files = [f for f in os.listdir(folder) if f.lower().endswith('.flac')]
    flac_files.sort()
    for cue_file in cue_files:
        cue_path = os.path.join(folder, cue_file)
        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
            cue_lines = f.readlines()
        new_cue_lines = []
        flac_idx = 0
        for line in cue_lines:
            if line.strip().startswith('FILE'):
                # Replace .wav with .flac and use the correct FLAC filename
                if flac_idx < len(flac_files):
                    new_file = flac_files[flac_idx]
                    # Keep the WAVE keyword for compatibility, but use .flac filename
                    new_cue_lines.append(f'FILE "{new_file}" WAVE\n')
                    flac_idx += 1
                else:
                    new_cue_lines.append(line)
            else:
                new_cue_lines.append(line)
        # --- DISABLE ALL DIRECT CUE WRITES ---
        # Commented out to prevent accidental overwrites. Use safe_update_cue from nfo_backend.py instead.
        # with open(cue_path, 'w', encoding='utf-8', newline='') as f:
        #     f.writelines(new_cue_lines)
        print('[BLOCKED] Direct .cue write skipped. Use safe_update_cue from nfo_backend.py instead.')

def restore_folder_name(folder):
    cue_path = find_cue_file(folder)
    if not cue_path:
        return
    orig_flacs = parse_cue_files(cue_path)
    if not orig_flacs:
        return
    # Guess original folder name from cue or first FLAC filename
    # Example: 01-Track.flac or Artist - Album (Year) [DiscogsID] -> try to remove Discogs pattern
    parent = os.path.dirname(folder)
    folder_base = os.path.basename(folder)
    # Remove Discogs pattern: (Year) [ID]
    new_base = re.sub(r' \([0-9]{4}\) \[[0-9]+\]$', '', folder_base)
    if new_base != folder_base:
        new_folder = os.path.join(parent, new_base)
        if not os.path.exists(new_folder):
            print(f"Renaming folder {folder_base} -> {new_base}")
            os.rename(folder, new_folder)
        else:
            print(f"[WARN] Target folder exists: {new_base}")

def main():
    for root, dirs, files in os.walk(ROOT_DIR):
        # Only operate on leaf dirs (those with FLACs)
        if any(f.lower().endswith('.flac') for f in files):
            print(f"Processing {root}")
            rename_flacs_to_cue(root)
            restore_folder_name(root)

if __name__ == "__main__":
    main()
