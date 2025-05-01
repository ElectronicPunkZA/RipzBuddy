import os
import re
import shutil
import tempfile
import mutagen
from mutagen.flac import FLAC

def robust_readlines(path):
    for enc in ('utf-8', 'cp1252', 'latin1'):
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not read {path} with any known encoding.")

def update_cue_file_safe(cue_path, flac_filenames):
    # Only keep REM, PERFORMER, TITLE, and DATE headers from the original
    lines = robust_readlines(cue_path)
    cue_headers = []
    for line in lines:
        if line.strip().upper().startswith(('REM', 'PERFORMER', 'TITLE', 'DATE')):
            cue_headers.append(line)
    new_lines = cue_headers[:]
    for idx, flac in enumerate(flac_filenames, 1):
        flac_path = os.path.join(os.path.dirname(cue_path), flac)
        try:
            audio = FLAC(flac_path)
            artist = audio.get('artist', [''])[0].strip()
            title = audio.get('title', [os.path.splitext(flac)[0]])[0].strip()
            bracketed = re.findall(r'\(([^)]*)\)|\[([^]]*)\]|\{([^}]*)\}', title)
            bracketed_info = [item for group in bracketed for item in group if item]
            remix = audio.get('remix', [""])[0].strip()
            mix = audio.get('mix', [""])[0].strip()
            version = audio.get('version', [""])[0].strip()
            subtitle = audio.get('subtitle', [""])[0].strip()
            extra_tags = [remix, mix, version, subtitle] + bracketed_info
            seen = set()
            extras = []
            for tag in extra_tags:
                tag_clean = tag.strip()
                if tag_clean and tag_clean.lower() not in title.lower() and tag_clean.lower() not in seen:
                    extras.append(tag_clean)
                    seen.add(tag_clean.lower())
            if extras:
                title_display = f"{re.sub(r'[\[\]{}()]', '', title).strip()} ({', '.join(extras)})"
            else:
                title_display = title
        except Exception:
            artist = ''
            title_display = os.path.splitext(flac)[0]
        new_lines.append(f'FILE "{flac}" WAVE\n')
        new_lines.append(f'  TRACK {idx:02d} AUDIO\n')
        new_lines.append(f'    TITLE "{title_display}"\n')
        if artist:
            new_lines.append(f'    PERFORMER "{artist}"\n')
        new_lines.append(f'    INDEX 01 00:00:00\n')
    directory = os.path.dirname(cue_path)
    fd, tmp_path = tempfile.mkstemp(suffix='.cue.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        shutil.move(tmp_path, cue_path)
        print(f"[OK] Rebuilt CUE for {cue_path} (minimal, compatible)")
    except Exception as e:
        print(f"[CRITICAL] Failed to rebuild CUE file: {cue_path}. Error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print(f"[RECOVERY] Original .cue left untouched: {cue_path}")
    return

def batch_update_cues(root_folder):
    for dirpath, dirnames, filenames in os.walk(root_folder):
        cue_files = [f for f in filenames if f.lower().endswith('.cue')]
        flac_files = sorted([f for f in filenames if f.lower().endswith('.flac')])
        if not cue_files or not flac_files:
            continue
        for cue_file in cue_files:
            cue_path = os.path.join(dirpath, cue_file)
            update_cue_file_safe(cue_path, flac_files)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python batch_update_cue_files.py <root_folder>")
        exit(1)
    batch_update_cues(sys.argv[1])
