#!/usr/bin/env python3
"""Small management CLI for the private deployment.

Usage:
    python manage.py hash-password           # prompt, print FAMILY_PASSWORD_HASH
    python manage.py hash-password "secret"  # non-interactive
    python manage.py init-db                 # create tables + default child
"""
import getpass
import sys

from werkzeug.security import generate_password_hash


def hash_password(argv):
    if argv:
        pw = argv[0]
    else:
        pw = getpass.getpass("New family password: ")
        again = getpass.getpass("Repeat password: ")
        if pw != again:
            print("Passwords did not match.", file=sys.stderr)
            return 1
    if len(pw) < 6:
        print("Please choose at least 6 characters.", file=sys.stderr)
        return 1
    print("\nAdd this line to your environment / .env / systemd unit:\n")
    print('FAMILY_PASSWORD_HASH=' + generate_password_hash(pw))
    return 0


def init_db(_argv):
    from app import create_app
    from app.db import init_db as _init
    app = create_app()
    with app.app_context():
        _init()
    print("Database initialised at:", app.config["DATABASE"])
    return 0


COMMANDS = {"hash-password": hash_password, "init-db": init_db}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
