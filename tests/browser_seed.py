"""Create disposable browser-test data; never point SENSO_DATA_DIR at production."""

from senso import config
from senso.auth import AuthStore
from senso.db.bean_repo import BeanRepository
from senso.db.database import open_database
from senso.domain.bean import BeanKind, validate_bean

if __name__ == "__main__":
    root = config.data_dir()
    if (root / "accounts.db").exists():
        raise SystemExit("Browser test requires a fresh disposable data directory")
    user = AuthStore(root).register("browser_smoke", "browser-coffee-ritual-2026")
    conn = open_database(user.directory(root) / "senso.db")
    BeanRepository(conn).create(validate_bean(BeanKind.TEA, "Browser test tea"))
    conn.close()
