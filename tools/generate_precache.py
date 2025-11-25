#!/usr/bin/env python3
"""
Generate a precache list by scanning project asset folders and inject it into service_worker.js.
Usage:
  python tools/generate_precache.py --root . --sw-path service_worker.js --out precache-manifest.json
This script:
- walks `web/` and `assets/` (configurable)
- excludes large files and source maps
- writes a backup of the original `service_worker.js`
- replaces the `PRECACHE_URLS` array in `service_worker.js`
- emits `precache-manifest.json` as a record
"""
import argparse
import json
import os
import re
import shutil
import time

EXCLUDE_EXT = {'.map', '.psd', '.zip', '.exe', '.dll', '.pyc', '.class', '.so', '.jar', '.log'}
EXCLUDE_DIRS = {'node_modules', '.git', 'build', '__pycache__'}
MAX_FILE_SIZE = 1_000_000  # 1 MB default maximum for precacheable file (adjustable)

DEFAULT_SCAN_PATHS = ['web', 'assets']
ADDITIONAL_ROOT_FILES = ['index.html', 'offline.html', 'manifest.json', 'web/index.html', 'web/offline.html']

PRECACHE_REGEX = re.compile(r"const\s+PRECACHE_URLS\s*=\s*\[[\s\S]*?\];", re.MULTILINE)


def should_exclude(path):
    if any(part in EXCLUDE_DIRS for part in path.split(os.sep)):
        return True
    ext = os.path.splitext(path)[1].lower()
    if ext in EXCLUDE_EXT:
        return True
    try:
        if os.path.getsize(path) > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def gather_files(root, scan_paths):
    urls = set()
    root = os.path.abspath(root)
    for rel_scan in scan_paths:
        scan_dir = os.path.join(root, rel_scan)
        if not os.path.exists(scan_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(scan_dir):
            # filter out excluded dirs
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace('\\', '/')
                if should_exclude(full):
                    continue
                urls.add('/' + rel)
    # add additional root files explicitly if present
    for r in ADDITIONAL_ROOT_FILES:
        full = os.path.join(root, r.replace('/', os.sep))
        if os.path.exists(full) and not should_exclude(full):
            rel = os.path.relpath(full, root).replace('\\', '/')
            urls.add('/' + rel)
    # Always include root
    urls.add('/')
    return sorted(urls)


def replace_precache_in_sw(sw_path, urls):
    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # build array string
    lines = ["\t'{}',".format(u) for u in urls]
    arr_body = '\n'.join(lines)
    new_array = 'const PRECACHE_URLS = [\n' + arr_body + '\n];'

    if PRECACHE_REGEX.search(content):
        new_content = PRECACHE_REGEX.sub(new_array, content)
    else:
        # fallback: try to inject after CACHE_NAME line
        marker = "const CACHE_NAME = `mindful-${CACHE_VERSION}`;"
        if marker in content:
            new_content = content.replace(marker, marker + '\n\n' + new_array)
        else:
            raise RuntimeError('Could not find PRECACHE_URLS placeholder or insertion point in service worker.')

    # backup
    bak = sw_path + '.bak.' + time.strftime('%Y%m%d%H%M%S')
    shutil.copy2(sw_path, bak)
    with open(sw_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return bak


def write_manifest(out_path, urls):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'precache': urls, 'generated_at': int(time.time())}, f, indent=2, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='.', help='Project root to scan')
    p.add_argument('--sw-path', default='service_worker.js', help='Path to the service worker file to update')
    p.add_argument('--out', default='precache-manifest.json', help='Output manifest file')
    p.add_argument('--max-size', type=int, default=MAX_FILE_SIZE, help='Max file size in bytes to include')
    p.add_argument('--scan-paths', nargs='*', default=DEFAULT_SCAN_PATHS, help='Relative paths to scan (space separated)')
    args = p.parse_args()

    globals()['MAX_FILE_SIZE'] = args.max_size

    root = os.path.abspath(args.root)
    sw_path = os.path.join(root, args.sw_path) if not os.path.isabs(args.sw_path) else args.sw_path

    print('Scanning', root)
    urls = gather_files(root, args.scan_paths)
    print('Found {} candidate files'.format(len(urls)))

    manifest_path = os.path.join(root, args.out)
    write_manifest(manifest_path, urls)
    print('Wrote manifest to', manifest_path)

    if not os.path.exists(sw_path):
        print('Service worker not found at', sw_path)
        return 2

    bak = replace_precache_in_sw(sw_path, urls)
    print('Backed up original service worker to', bak)
    print('Updated', sw_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
