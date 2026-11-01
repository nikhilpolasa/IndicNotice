"""Local operator bootstrap for an explicitly authenticated account."""
from __future__ import annotations

import argparse
import getpass
import sys

from services.auth.store import AuthStore, InvalidCredentials


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage local IndicNotice administrator access.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    promote = subparsers.add_parser("promote", help="Promote an existing account after password verification")
    promote.add_argument("--email", required=True)
    args = parser.parse_args(argv)
    if input(f"Promote {args.email.strip()} to IndicNotice administrator? Type PROMOTE to continue: ").strip() != "PROMOTE":
        print("No changes made.")
        return 1
    password = getpass.getpass("Account password: ")
    try:
        AuthStore().grant_admin(args.email, password)
    except (InvalidCredentials, ValueError):
        print("Account authentication failed; no changes made.")
        return 1
    print("Administrator access granted to the authenticated account.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
