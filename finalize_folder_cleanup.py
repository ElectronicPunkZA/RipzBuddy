import os
import shutil
import re

def is_cue_file(fname):
    return fname.lower().endswith('.cue')

def is_strict_art(fname):
    return fname.lower() == 'folder.jpg'

def finalize_folder(folder):
    # Remove backup_legacy_files directory if present
    backup_dir = os.path.join(folder, "backup_legacy_files")
    if os.path.isdir(backup_dir):
        print(f"[CLEANUP] Removing legacy backup directory: {backup_dir}")
        try:
            for root, dirs, files in os.walk(backup_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(backup_dir)
        except Exception as e:
            print(f"[ERROR] Failed to remove {backup_dir}: {e}")
    # Delete any .flac files not matching the correct pattern
    flac_pattern = re.compile(r'^\d{2} - .+ - .+\.flac$', re.IGNORECASE)
    for fname in os.listdir(folder):
        if fname.lower().endswith('.flac') and not flac_pattern.match(fname):
            full_path = os.path.join(folder, fname)
            print(f"[CLEANUP] Deleting legacy FLAC: {full_path}")
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"[ERROR] Could not delete {full_path}: {e}")
    # 1. CUE files: do NOT generate or rename any CUEs, only process existing ones
    cue_files = [f for f in os.listdir(folder) if is_cue_file(f)]
    # Do not move or rename cues, just leave them as-is
    # 2. Images: move all images except 'folder.jpg' to _legacy
    legacy_dir = os.path.join(folder, '_legacy')
    os.makedirs(legacy_dir, exist_ok=True)
    for fname in os.listdir(folder):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png')) and fname.lower() != 'folder.jpg':
            shutil.move(os.path.join(folder, fname), os.path.join(legacy_dir, fname))
    # 3. Other legacy files (optional): move everything that's not a FLAC, cue, id.tsh, or folder.jpg
    for fname in os.listdir(folder):
        if fname.lower() not in [f.lower() for f in cue_files] + ['folder.jpg', 'id.tsh'] and not fname.lower().endswith('.flac'):
            if fname != '_legacy':
                shutil.move(os.path.join(folder, fname), os.path.join(legacy_dir, fname))
    print(f"[OK] Finalized {folder}. Images and legacy files moved to _legacy. CUE files left untouched. Only correct FLACs remain.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python finalize_folder_cleanup.py <parent_folder>")
        sys.exit(1)
    parent = sys.argv[1]
    for sub in os.listdir(parent):
        folder = os.path.join(parent, sub)
        if os.path.isdir(folder):
            finalize_folder(folder)
