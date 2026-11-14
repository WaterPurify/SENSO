"""Offline operator backups. age encryption; streaming verification; empty-target restore.

Run through backup.ps1 with the application stopped. No plaintext archive is written.
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

FORMAT = 1
MANIFEST = "SENSO_BACKUP.json"
MAX_MANIFEST = 8 * 1024 * 1024


def digest(stream):
    result = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def safe_name(name):
    parts = PurePosixPath(name).parts
    if (
        not parts
        or name != PurePosixPath(name).as_posix()
        or any(part in (".", "..") for part in parts)
        or name.startswith("/")
        or "\\" in name
        or ":" in name
    ):
        raise ValueError("Unsafe archive path")
    return name


def validate_data(root):
    """Check SQLite integrity, known schema bounds, user IDs and photo references."""
    accounts = root / "accounts.db"
    if not accounts.is_file():
        raise ValueError("accounts.db is missing")
    versions = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Links and special files are not supported")
        if path.suffix != ".db":
            continue
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("SQLite integrity check failed")
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("SQLite foreign key check failed")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            versions[path.relative_to(root).as_posix()] = version
            if path == accounts:
                for (user_id,) in conn.execute("SELECT id FROM users"):
                    if uuid.UUID(user_id).hex != user_id:
                        raise ValueError("Invalid account ID")
            else:
                if not 1 <= version <= 7:
                    raise ValueError("Unsupported record schema; use matching backup tools")
                for (name,) in conn.execute(
                    "SELECT photo_path FROM beans WHERE photo_path IS NOT NULL"
                ):
                    if not name:
                        continue
                    if safe_name(name) != PurePosixPath(name).name:
                        raise ValueError("Invalid photo reference")
                    if not (path.parent / "photos" / name).is_file():
                        raise ValueError("Referenced photo is missing")
        finally:
            conn.close()
    return versions


def inventory(root):
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Links are not supported")
        if path.is_file():
            name = safe_name(path.relative_to(root).as_posix())
            if name == MANIFEST:
                raise ValueError("Reserved manifest filename")
            with path.open("rb") as stream:
                files[name] = {"size": path.stat().st_size, "sha256": digest(stream)}
        elif not path.is_dir():
            raise ValueError("Special files are not supported")
    return files


def unpack(archive, target=None):
    """Verify a decrypted stream; extract only regular files with exact manifest names."""
    with tarfile.open(fileobj=archive, mode="r|") as tar:
        first = tar.next()
        if not first or first.name != MANIFEST or not first.isfile() or first.size > MAX_MANIFEST:
            raise ValueError("Missing/invalid backup manifest")
        manifest = json.load(tar.extractfile(first))
        if manifest["format"] != FORMAT:
            raise ValueError("Unsupported backup format")
        expected = manifest["files"]
        if "accounts.db" not in expected:
            raise ValueError("Missing accounts database")
        for name in expected:
            safe_name(name)
        seen = set()
        while member := tar.next():
            name = safe_name(member.name)
            if name in seen or not member.isfile() or name not in expected:
                raise ValueError("Unexpected archive entry")
            if member.size != expected[name]["size"]:
                raise ValueError("File size mismatch")
            stream = tar.extractfile(member)
            checksum = hashlib.sha256()
            output = None
            try:
                if target is not None:
                    path = target / name
                    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    output = path.open("xb")
                    path.chmod(0o600)
                while chunk := stream.read(1024 * 1024):
                    checksum.update(chunk)
                    if output:
                        output.write(chunk)
            finally:
                if output:
                    output.close()
            if checksum.hexdigest() != expected[name]["sha256"]:
                raise ValueError("File checksum mismatch")
            seen.add(name)
        if seen != set(expected):
            raise ValueError("Incomplete backup")
    # Read through the final age authentication tag (tar can stop before EOF).
    while archive.read(1024 * 1024):
        pass
    return manifest


def decrypt(source, identity, target=None):
    with subprocess.Popen(
        ["age", "--decrypt", "--identity", str(identity), str(source)], stdout=subprocess.PIPE
    ) as process:
        try:
            manifest = unpack(process.stdout, target)
        except BaseException:
            process.kill()
            raise
        finally:
            process.stdout.close()
        if process.wait() != 0:
            raise ValueError("Backup decryption/authentication failed")
    return manifest


def backup(root, destination, recipient, identity):
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing backup")
    schemas = validate_data(root)
    manifest = {
        "format": FORMAT,
        "created_at": datetime.now(UTC).isoformat(),
        "app_version": "0.9.0",
        "schemas": schemas,
        "files": inventory(root),
    }
    payload = json.dumps(manifest, ensure_ascii=False).encode()
    if len(payload) > MAX_MANIFEST:
        raise ValueError("Backup manifest is too large")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".senso-", suffix=".age", dir=destination.parent)
    temporary = Path(temporary)
    try:
        with (
            os.fdopen(fd, "wb") as encrypted,
            subprocess.Popen(
                ["age", "--recipient", recipient], stdin=subprocess.PIPE, stdout=encrypted
            ) as process,
        ):
            try:
                with tarfile.open(fileobj=process.stdin, mode="w|") as tar:
                    header = tarfile.TarInfo(MANIFEST)
                    header.size = len(payload)
                    tar.addfile(header, io.BytesIO(payload))
                    for name in manifest["files"]:
                        tar.add(root / name, arcname=name, recursive=False)
            finally:
                process.stdin.close()
            if process.wait() != 0:
                raise ValueError("Encryption failed")
        decrypt(temporary, identity)  # No plaintext files, verify before publishing.
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def restore(source, identity, target):
    if not target.is_dir() or any(target.iterdir()):
        raise ValueError("Restore requires an existing EMPTY directory/volume")
    try:
        manifest = decrypt(source, identity, target)
        if validate_data(target) != manifest["schemas"]:
            raise ValueError("Schema inventory mismatch")
        # Production app UID/GID; operations image runs as root only for ownership.
        if os.geteuid() == 0:
            for path in [target, *target.rglob("*")]:
                os.chown(path, 10001, 10001)
        for path in [target, *target.rglob("*")]:
            path.chmod(0o700 if path.is_dir() else 0o600)
    except BaseException:
        for path in target.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "verify", "restore"])
    parser.add_argument("--data", type=Path, default=Path("/data"))
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--identity", type=Path, default=Path("/keys/identity.txt"))
    parser.add_argument("--recipient")
    args = parser.parse_args()
    if args.action == "backup":
        if not args.recipient:
            parser.error("--recipient is required")
        backup(args.data, args.file, args.recipient, args.identity)
    elif args.action == "verify":
        decrypt(args.file, args.identity)
    else:
        restore(args.file, args.identity, args.data)
    print(f"{args.action}: verified successfully")


if __name__ == "__main__":
    main()
