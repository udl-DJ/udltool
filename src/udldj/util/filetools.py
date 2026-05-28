import os

IGNORE_FOLDERS = ['System Volume Information', '$RECYCLE.BIN', 'thumbs.db', '.DS_Store', '.Spotlight-V100']
IGNORE_PREFIXES = ['.']
IGNORE_SUFFIXES = [*IGNORE_FOLDERS, '~']

def walk_filtered(
    path,
    yield_files=False,
    yield_dirs=False,
    use_relpath=False,
    ignore_folders=IGNORE_FOLDERS,
    ignore_prefixes=IGNORE_PREFIXES,
    ignore_suffixes=IGNORE_PREFIXES
):
    for root, dirs, files in os.walk(path):
        if any(root.endswith(s) for s in ignore_folders): continue

        root_rel = root
        if use_relpath:
            root_rel = root[len(path):]
            if root_rel.startswith(os.sep):
                root_rel = root_rel[1:]

        if yield_dirs:
            for _dir in dirs:
                if any(_dir.startswith(s) for s in ignore_prefixes): continue
                if any(_dir.endswith(s) for s in ignore_suffixes): continue

                yield os.path.join(root_rel, _dir)
        
        if yield_files:
            for file in files:
                if any(file.startswith(s) for s in ignore_prefixes): continue
                if any(file.endswith(s) for s in ignore_suffixes): continue

                yield os.path.join(root_rel, file)