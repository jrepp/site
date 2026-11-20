#!/usr/bin/env python3
"""Publish a profile build while preserving the existing site and archives."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ('avatar.jpg', 'favicon.svg', 'profile.css', 'profile.js', 'profile.json', 'sources.json')


def replace_file(source: Path, target: Path) -> None:
    fd, name = tempfile.mkstemp(prefix='.profile-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as out, source.open('rb') as src:
            shutil.copyfileobj(src, out)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, 0o644)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install'])
    parser.add_argument('--env', choices=['prod', 'dev'], default='prod')
    parser.add_argument('--src', type=Path, default=ROOT / 'build/profile')
    parser.add_argument('--dest', type=Path)
    args = parser.parse_args()
    src = args.src.resolve()
    dest = args.dest or Path('/srv/www/jrepp.com' if args.env == 'prod' else '/srv/www/jrepp.com-dev')
    if not dest.is_dir():
        parser.error(f'destination must already exist: {dest}')
    files = [src / 'index.html', *(src / 'assets' / name for name in ASSETS)]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        parser.error('missing profile files: ' + ', '.join(missing))
    with (dest.parent / ('.' + dest.name + '.profile-publish.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        backups = dest.parent / 'backups'
        backups.mkdir(mode=0o755, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = backups / (dest.name + '-before-profile-' + stamp)
        shutil.copytree(dest, backup, symlinks=True, copy_function=shutil.copy2)
        assets = dest / 'assets'
        assets.mkdir(mode=0o755, exist_ok=True)
        for name in ASSETS:
            replace_file(src / 'assets' / name, assets / name)
        replace_file(src / 'index.html', dest / 'index.html')
        print(f'backup={backup}\ninstalled={dest}')


if __name__ == '__main__':
    main()
