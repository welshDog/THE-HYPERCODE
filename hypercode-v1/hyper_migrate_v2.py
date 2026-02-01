import os
import shutil
import hashlib
import re
from pathlib import Path

# ================= CONFIGURATION =================
OLD_REPO_PATH = "hypercode-v1"      # <- old code + research
NEW_REPO_PATH = "hypercode-v2"      # <- new clean repo
EXTRA_RESEARCH_PATH = "hypercode-research"  # <- extra DB/research repo
INCLUDE_EXTRA_RESEARCH = True
DRY_RUN = False  # Set to False to actually copy
# =================================================

def get_file_hash(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def is_junk_name(filename):
    patterns = [
        r'\(\d+\)',          # file (1).py
        r'^copy of',         # copy of file
        r'\.bak$',           # .bak
        r'\.tmp$',           # .tmp
        r'^\.DS_Store$',     # macOS
        r'^Thumbs\.db$',     # Windows
        r'~$'                # backup~
    ]
    for p in patterns:
        if re.search(p, filename, re.IGNORECASE):
            return True
    return False

def scan_repo(root):
    file_map = {}
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
        for name in filenames:
            if is_junk_name(name):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            file_map[rel] = full
    return file_map

def target_path_for(rel_path, repo_root):
    # If already in src/tests/docs/etc, keep structure
    if rel_path.startswith(("src/", "tests/", "docs/", ".github/", "data/")):
        return repo_root / rel_path
    # Otherwise treat as src/hypercode content
    return repo_root / "src" / "hypercode" / rel_path

def migrate(src_map, new_root, label):
    print(f"\n=== Migrating from {label} ===")
    moved = 0
    skipped_same = 0
    for rel, src_full in src_map.items():
        dst = target_path_for(rel, new_root)

        if dst.exists():
            # compare hashes
            try:
                if get_file_hash(src_full) == get_file_hash(dst):
                    print(f"[SKIP] Same already in new: {rel}")
                    skipped_same += 1
                    continue
                else:
                    print(f"[WARN] Different version exists, keep NEW: {rel}")
                    continue
            except Exception as e:
                print(f"⚠️  Could not compare {rel}: {e}")
                continue

        if DRY_RUN:
            print(f"[DRY RUN] Would copy: {rel} -> {dst.relative_to(new_root)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_full, dst)
            print(f"[COPIED] {rel}")
        moved += 1

    print(f"\nSummary for {label}: moved={moved}, identical_skipped={skipped_same}")

def main():
    # Set console to support UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    old_root = Path(OLD_REPO_PATH)
    new_root = Path(NEW_REPO_PATH)

    print("\n=== HyperCode V2 Migration ===\n")

    # 1) scan old code repo
    old_files = scan_repo(old_root)
    print(f"OLD (hypercode-V1): {len(old_files)} files detected")

    # 2) optionally scan extra research repo
    extra_files = {}
    if INCLUDE_EXTRA_RESEARCH and os.path.isdir(EXTRA_RESEARCH_PATH):
        extra_root = Path(EXTRA_RESEARCH_PATH)
        extra_files = scan_repo(extra_root)
        print(f"EXTRA (hypercode-research): {len(extra_files)} files detected")

    # 3) migrate
    migrate(old_files, new_root, "hypercode-V1")
    if extra_files:
        migrate(extra_files, new_root, "hypercode-research")

    print("\nDone. Set DRY_RUN = False when you're happy with the plan.")

if __name__ == "__main__":
    main()
