import os
import re

# Set your root music directory here
ROOT_DIR = r"F:\CD COLLECTION\Test Centre 2"

# Regex for correct FLAC naming: 01 - Artist - Title.flac
flac_pattern = re.compile(r'^\d{2} - .+ - .+\.flac$', re.IGNORECASE)

# Files/folders that should NOT exist
UNWANTED_DIRS = ["backup_legacy_files", "_legacy"]

# Files that should ONLY exist if matching rules
ALLOWED_EXTENSIONS = {'.flac', '.cue', '.nfo', '.sfv', '.m3u', '.jpg', '.jpeg', '.png', '.log', '.tsh'}
ALWAYS_ALLOWED = {'folder.jpg', 'id.tsh'}


def audit_release_folder(folder):
    issues = []
    # Check for unwanted directories
    for name in os.listdir(folder):
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path) and name in UNWANTED_DIRS:
            issues.append(f"[DIR] Unwanted directory present: {full_path}")
    # Check for incorrectly named FLACs
    for name in os.listdir(folder):
        if name.lower().endswith('.flac') and not flac_pattern.match(name):
            issues.append(f"[FLAC] Legacy or non-conforming FLAC: {os.path.join(folder, name)}")
    # Check for unexpected files
    for name in os.listdir(folder):
        ext = os.path.splitext(name)[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS and name.lower() not in ALWAYS_ALLOWED:
            issues.append(f"[FILE] Unexpected file: {os.path.join(folder, name)}")
    return issues

def audit_all_release_folders(root_dir):
    all_issues = []
    for entry in os.listdir(root_dir):
        full_path = os.path.join(root_dir, entry)
        if os.path.isdir(full_path):
            issues = audit_release_folder(full_path)
            if issues:
                all_issues.append(f"\n[ISSUES in {full_path}]:")
                all_issues.extend(issues)
    if all_issues:
        print("\nAUDIT REPORT: Non-conforming files/folders detected:")
        for issue in all_issues:
            print(issue)
    else:
        print("\nAUDIT REPORT: All folders are clean and conform to the rules.")

if __name__ == "__main__":
    audit_all_release_folders(ROOT_DIR)
