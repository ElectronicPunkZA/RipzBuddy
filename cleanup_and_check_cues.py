import os
import re

ROOT = r"F:/CD COLLECTION/Test Centre 2"

# Patterns for per-disc cues
PER_DISC_CUE = re.compile(r"cd\d+\.cue", re.IGNORECASE)

# Acceptable single-disc cue name (album base name)
def get_album_base(folder):
    # Remove trailing slashes if any
    folder = folder.rstrip("/\\")
    return os.path.basename(folder)

def is_per_disc_cue(filename):
    return PER_DISC_CUE.fullmatch(filename) is not None

def is_valid_cue_line(line, flac_files):
    line = line.strip()
    if line.upper().startswith('FILE'):
        m = re.match(r'FILE\s+"(.+?)"', line, re.IGNORECASE)
        if m:
            fname = m.group(1)
            return fname in flac_files
        return False
    return True  # ignore non-FILE lines

def cleanup_and_check():
    for folder in os.listdir(ROOT):
        folder_path = os.path.join(ROOT, folder)
        if not os.path.isdir(folder_path):
            continue
        cues = [f for f in os.listdir(folder_path) if f.lower().endswith('.cue')]
        flacs = [f for f in os.listdir(folder_path) if f.lower().endswith('.flac')]
        album_base = get_album_base(folder_path)
        per_disc_cues = [f for f in cues if is_per_disc_cue(f)]
        merged_cues = [f for f in cues if not is_per_disc_cue(f)]
        # If per-disc cues exist, delete all merged cues
        if per_disc_cues:
            for mc in merged_cues:
                cue_path = os.path.join(folder_path, mc)
                print(f"[CLEANUP] Deleting legacy/merged cue: {cue_path}")
                try:
                    os.remove(cue_path)
                except Exception as e:
                    print(f"[WARN] Could not delete {cue_path}: {e}")
        # Check all cues for FILE line validity
        for cue in cues:
            cue_path = os.path.join(folder_path, cue)
            try:
                with open(cue_path, encoding='utf-8') as f:
                    lines = f.readlines()
                valid = True
                for line in lines:
                    if not is_valid_cue_line(line, flacs):
                        print(f"[ERROR] In {cue_path}: FILE line references missing FLAC file.")
                        valid = False
                if valid:
                    print(f"[OK] {cue_path}: All FILE lines match FLAC files.")
            except Exception as e:
                print(f"[ERROR] Could not check {cue_path}: {e}")

if __name__ == "__main__":
    cleanup_and_check()
