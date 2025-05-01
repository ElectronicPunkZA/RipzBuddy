import os
import shutil
import re

# Path to the folder for Monster Hits Volume 4
FOLDER = r"F:/CD COLLECTION/TEST DIRECTORY/Various - Monster_Hits_Volume_4"
CUE = None
CUE_BAK = None

# Find cue and backup cue
for f in os.listdir(FOLDER):
    if f.lower().endswith('.cue'):
        if f.lower().endswith('.bak'):
            CUE_BAK = os.path.join(FOLDER, f)
        else:
            CUE = os.path.join(FOLDER, f)

if not CUE_BAK:
    # Try the .cue.bak naming
    for f in os.listdir(FOLDER):
        if f.lower().endswith('.cue.bak'):
            CUE_BAK = os.path.join(FOLDER, f)

if not CUE_BAK or not CUE:
    print("[ERROR] Could not find both .cue and .cue.bak in folder.")
    exit(1)

# Step 1: Restore the original cue file
shutil.copy2(CUE_BAK, CUE)
print(f"Restored original cue file from backup: {os.path.basename(CUE_BAK)} -> {os.path.basename(CUE)}")

# Step 2: Rename FLAC files to match cue
# Parse cue for file order
flac_names = []
with open(CUE, encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = re.match(r'\s*FILE\s+"([^"]+)"\s+WAVE', line)
        if m:
            flac_names.append(m.group(1))

curr_flacs = sorted([f for f in os.listdir(FOLDER) if f.lower().endswith('.flac')])

if len(flac_names) != len(curr_flacs):
    print(f"[ERROR] FLAC count mismatch: cue={len(flac_names)}, folder={len(curr_flacs)}")
    print("Please check the folder manually.")
    exit(1)

# Map and rename
for old, new in zip(curr_flacs, flac_names):
    if old != new:
        src = os.path.join(FOLDER, old)
        dst = os.path.join(FOLDER, new)
        if os.path.exists(dst):
            print(f"[WARN] Target exists: {new}, skipping.")
            continue
        print(f"Renaming {old} -> {new}")
        os.rename(src, dst)

# --- DISABLE ALL DIRECT CUE WRITES (except restore from backup) ---
# Only allow shutil.copy2 for restoring backup. Block any other .cue write logic.
# with open(CUE, 'w', encoding='utf-8') as f:
#     f.writelines(new_lines)
print('[BLOCKED] Direct .cue write skipped. Use safe_update_cue from nfo_backend.py instead.')

print("Done. Please verify the folder and cue file.")
