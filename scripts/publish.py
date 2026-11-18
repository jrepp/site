#!/usr/bin/env -S uv run --python 3.14.2 python
import argparse
import os
import shutil
import sys
import tempfile
import pwd
import grp


DEFAULT_ENV = "prod"
DEFAULT_DIR_MODE = 0o755
DEFAULT_FILE_MODE = 0o644

CONFIG = {
    "prod": {
        "src": "build/site",
        "dest": "/srv/www/jrepp.com",
        "owner": "root",
        "group": "www-data",
    },
    "dev": {
        "src": "build/site",
        "dest": "/srv/www/jrepp.com-dev",
        "owner": "root",
        "group": "www-data",
    },
}


def resolve_repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_path(repo_root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(repo_root, path)


def set_permissions(root: str, dir_mode: int, file_mode: int) -> None:
    for base, dirs, files in os.walk(root):
        for name in dirs:
            os.chmod(os.path.join(base, name), dir_mode)
        for name in files:
            os.chmod(os.path.join(base, name), file_mode)
    os.chmod(root, dir_mode)

def resolve_owner(user: str | None, group: str | None) -> tuple[int | None, int | None]:
    uid = None
    gid = None
    if user:
        uid = pwd.getpwnam(user).pw_uid
    if group:
        gid = grp.getgrnam(group).gr_gid
    return uid, gid


def set_owner(root: str, user: str | None, group: str | None) -> None:
    uid, gid = resolve_owner(user, group)
    if uid is None and gid is None:
        return
    for base, dirs, files in os.walk(root):
        for name in dirs:
            os.chown(os.path.join(base, name), uid or -1, gid or -1)
        for name in files:
            os.chown(os.path.join(base, name), uid or -1, gid or -1)
    os.chown(root, uid or -1, gid or -1)


def install_tree(
    src: str,
    dest: str,
    dir_mode: int,
    file_mode: int,
    owner: str | None,
    group: str | None,
) -> None:
    dest_parent = os.path.dirname(dest)
    os.makedirs(dest_parent, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=dest_parent) as tmp_dir:
        stage_dir = os.path.join(tmp_dir, "site")
        shutil.copytree(src, stage_dir)
        set_permissions(stage_dir, dir_mode, file_mode)
        set_owner(stage_dir, owner, group)

        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.replace(stage_dir, dest)


def check_permissions(dest: str) -> bool:
    dest_parent = os.path.dirname(dest)
    if not os.path.isdir(dest_parent):
        return True
    if os.access(dest_parent, os.W_OK | os.X_OK):
        return True
    print(
        "Permission denied writing to %s (run with sudo or fix ownership)."
        % dest_parent,
        file=sys.stderr,
    )
    return False


def parse_mode(value: str) -> int:
    return int(value, 8)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install a published Jekyll build to a stable host path."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument(
        "--env",
        default=os.getenv("PUBLISH_ENV", DEFAULT_ENV),
        choices=sorted(CONFIG.keys()),
        help="Publish environment (default: prod).",
    )
    install.add_argument(
        "--src",
        help="Build output to install (overrides config).",
    )
    install.add_argument(
        "--dest",
        help="Target install path (overrides config).",
    )
    install.add_argument(
        "--owner",
        help="File owner (overrides config).",
    )
    install.add_argument(
        "--group",
        help="File group (overrides config).",
    )
    install.add_argument(
        "--dir-mode",
        default=os.getenv("PUBLISH_DIR_MODE", oct(DEFAULT_DIR_MODE)),
        type=parse_mode,
        help="Directory mode in octal (default: 0755).",
    )
    install.add_argument(
        "--file-mode",
        default=os.getenv("PUBLISH_FILE_MODE", oct(DEFAULT_FILE_MODE)),
        type=parse_mode,
        help="File mode in octal (default: 0644).",
    )
    return parser


def main(argv: list[str]) -> int:
    repo_root = resolve_repo_root()
    parser = build_parser()
    args = parser.parse_args(argv)

    env_config = CONFIG[args.env]
    src = resolve_path(repo_root, args.src or env_config["src"])
    dest = resolve_path(repo_root, args.dest or env_config["dest"])
    owner = args.owner or env_config.get("owner")
    group = args.group or env_config.get("group")
    if not os.path.isdir(src):
        print("Missing publish source: %s" % src, file=sys.stderr)
        return 2
    if not check_permissions(dest):
        return 2
    install_tree(src, dest, args.dir_mode, args.file_mode, owner, group)
    print("installed=%s" % dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
