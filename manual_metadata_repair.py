import sys
import os
from nfo_backend import generate_missing_metadata_files

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python manual_metadata_repair.py <folder>")
        sys.exit(1)
    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        sys.exit(1)
    print(f"[INFO] Generating missing metadata for: {folder}")
    generate_missing_metadata_files(folder)
    print("[DONE] Metadata repair complete.")
