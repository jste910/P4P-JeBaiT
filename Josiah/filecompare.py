import os
import hashlib
import difflib
import argparse

def sha256sum(path, chunk_size=65536):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def build_file_map(root):
    file_map = {}
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root)
            file_map[rel_path] = full_path
    return file_map

def is_text_file(path):
    try:
        with open(path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' not in chunk
    except:
        return False
    
def compare_folders(folder_a, folder_b, show_diff = False, ignore=None):
    if ignore is None:
        ignore = []
    else:
        ignore = set(ignore)
    
    # if the folder_a and foler_b are files, just compare them directly
    if os.path.isfile(folder_a) and os.path.isfile(folder_b):
        hash_a = sha256sum(folder_a)
        hash_b = sha256sum(folder_b)
        if hash_a == hash_b:
            print("Files are identical")
        else:
            print("Files are different")
            if show_diff and is_text_file(folder_a) and is_text_file(folder_b):
                print(f"\n--- DIFF: {folder_a} vs {folder_b} ---")
                try:
                    with open(folder_a, 'r', encoding='utf-8', errors='replace') as fa:
                        a_lines = fa.readlines()
                    with open(folder_b, 'r', encoding='utf-8', errors='replace') as fb:
                        b_lines = fb.readlines()

                    diff = difflib.unified_diff(a_lines, b_lines, fromfile=folder_a, tofile=folder_b, lineterm='')
                    for line in diff:
                        print(line.rstrip())
                except Exception as e:
                    print(f"Could not diff files: {e}")
        return
    
    files_a = build_file_map(folder_a)
    files_b = build_file_map(folder_b)



    paths_a = set(files_a.keys())
    paths_b = set(files_b.keys())
    only_a = sorted(paths_a - paths_b)
    only_b = sorted(paths_b - paths_a)
    common = sorted(paths_a & paths_b)

    changed = []

    print("\n=== ONLY IN FOLDER A ===")
    for path in only_a:
        if not any(pattern in path for pattern in ignore):
            print(f"  {path}")

    print("\n=== ONLY IN FOLDER B ===")
    for path in only_b:
        if not any(pattern in path for pattern in ignore):
            print(f"  {path}")

    print("\n=== COMMON FILES ===")
    for path in common:
        hash_a = sha256sum(files_a[path])
        hash_b = sha256sum(files_b[path])
        
        if hash_a != hash_b:
            changed.append(path)
            print(path)
            if show_diff:
                file_a = files_a[path]
                file_b = files_b[path]
                if is_text_file(file_a) and is_text_file(file_b):
                    print(f"\n--- DIFF: {path} ---")
                try:
                    with open(file_a, 'r', encoding='utf-8', errors='replace') as fa:
                        a_lines = fa.readlines()
                    with open(file_b, 'r', encoding='utf-8', errors='replace') as fb:
                        b_lines = fb.readlines()

                    diff = difflib.unified_diff(a_lines, b_lines, fromfile=f'FolderA/{path}', tofile=f'FolderB/{path}', lineterm='')
                    for line in diff:
                        print(line.rstrip())
                except Exception as e:
                    print(f"Could not diff {path}: {e}")

                print()
            
            print("\n=== SUMMARY ===")
            print(f"Only in Folder A: {len(only_a)}")
            print(f"Only in Folder B: {len(only_b)}")
            print(f"Changed: {len(changed)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two folders recursively")
    parser.add_argument("folder_a")
    parser.add_argument("folder_b")
    parser.add_argument("--diff", action="store_true", help="Show line-by-line differences for changed files")
    parser.add_argument("--ignore", nargs='*', default=[], help="List of file patterns to ignore (not implemented yet)")
    args = parser.parse_args()
    compare_folders(args.folder_a, args.folder_b, show_diff=args.diff, ignore=args.ignore)