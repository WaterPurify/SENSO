"""Operator-only retry for interrupted deletions; stop the app before running."""

import argparse

from senso import config
from senso.auth import AuthStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list-deletions", "finish-deletion"])
    parser.add_argument("user_id", nargs="?")
    args = parser.parse_args()
    store = AuthStore(config.data_dir())
    if args.action == "list-deletions":
        with store.connection() as conn:
            for row in conn.execute("SELECT id, username FROM users WHERE deleting = 1"):
                print(row["id"], row["username"])
    else:
        if not args.user_id:
            parser.error("user_id is required")
        store.finish_delete(args.user_id)
        print("Deletion completed.")


if __name__ == "__main__":
    main()
