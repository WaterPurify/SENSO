import io
import json
import shutil
import subprocess
import tarfile

import pytest
from ops.backup import MANIFEST, backup, decrypt, inventory, restore, unpack

from senso import auth
from senso.auth import AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean


@pytest.fixture
def keys(tmp_path):
    if not shutil.which("age") or not shutil.which("age-keygen"):
        pytest.skip("age tools required; installed by CI and ops/Dockerfile")
    identity = tmp_path / "identity.txt"
    subprocess.run(["age-keygen", "-o", str(identity)], check=True, capture_output=True)
    recipient = subprocess.check_output(["age-keygen", "-y", str(identity)], text=True).strip()
    return identity, recipient


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "ITERATIONS", 1000)
    root = tmp_path / "data"
    store = AuthStore(root)
    user = store.register("alice", "safe-test-password-123")
    directory = user.directory(root)
    photos = directory / "photos"
    photos.mkdir()
    (photos / "photo.jpg").write_bytes(b"test-photo")
    conn = open_database(directory / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.TEA, "세작"), photo_path="photo.jpg")
    conn.close()
    return root


def test_encrypted_round_trip_and_no_plaintext_archive(data, keys, tmp_path):
    identity, recipient = keys
    source = tmp_path / "senso.tar.age"
    backup(data, source, recipient, identity)
    assert source.read_bytes().startswith(b"age-encryption.org/")
    assert b"test-photo" not in source.read_bytes()
    assert not list(tmp_path.glob(".senso-*"))
    manifest = decrypt(source, identity)
    assert manifest["format"] == 1 and manifest["schemas"]["accounts.db"] == 0
    target = tmp_path / "restored"
    target.mkdir()
    restore(source, identity, target)
    assert inventory(target) == inventory(data)
    assert AuthStore(target).login("alice", "safe-test-password-123")
    with pytest.raises(ValueError, match="EMPTY"):
        restore(source, identity, data)


def test_wrong_key_tampering_and_cleanup(data, keys, tmp_path):
    identity, recipient = keys
    source = tmp_path / "senso.tar.age"
    backup(data, source, recipient, identity)
    wrong = tmp_path / "wrong.txt"
    subprocess.run(["age-keygen", "-o", str(wrong)], check=True, capture_output=True)
    with pytest.raises((ValueError, tarfile.ReadError)):
        decrypt(source, wrong)
    damaged = bytearray(source.read_bytes())
    damaged[-1] ^= 1
    source.write_bytes(damaged)
    target = tmp_path / "restored"
    target.mkdir()
    with pytest.raises((ValueError, tarfile.ReadError, EOFError)):
        restore(source, identity, target)
    assert not list(target.iterdir())


def test_missing_photos_refuse_backup(data, keys, tmp_path):
    identity, recipient = keys
    next(data.rglob("photo.jpg")).unlink()
    with pytest.raises(ValueError, match="photo"):
        backup(data, tmp_path / "bad.age", recipient, identity)
    assert not (tmp_path / "bad.age").exists()


@pytest.mark.parametrize("name", ["../escape", "/absolute", "users/../../escape", "C:/escape"])
def test_restore_rejects_archive_path_traversal(name):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        payload = json.dumps({"format": 1, "files": {"accounts.db": {}, name: {}}}).encode()
        header = tarfile.TarInfo(MANIFEST)
        header.size = len(payload)
        tar.addfile(header, io.BytesIO(payload))
    stream.seek(0)
    with pytest.raises(ValueError, match="Unsafe"):
        unpack(stream)
