#!/usr/bin/env python3
"""
Benutzer verwalten:
  python manage_users.py add     – Benutzer anlegen
  python manage_users.py remove  – Benutzer entfernen
  python manage_users.py list    – Alle Benutzer anzeigen
"""
import sys
import json
import uuid
import hashlib
import getpass
from pathlib import Path

USERS_FILE = Path(__file__).parent / "users.json"


def hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = uuid.uuid4().hex
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${dk.hex()}"


def load() -> dict:
    return json.loads(USERS_FILE.read_text()) if USERS_FILE.exists() else {}


def save(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))


cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

if cmd == "add":
    email = input("E-Mail (@b-ite.de): ").strip().lower()
    if not email.endswith("@b-ite.de"):
        print("Fehler: Nur @b-ite.de Adressen erlaubt.")
        sys.exit(1)
    password = getpass.getpass("Passwort: ")
    if len(password) < 8:
        print("Fehler: Passwort muss mindestens 8 Zeichen haben.")
        sys.exit(1)
    users = load()
    users[email] = hash_password(password)
    save(users)
    print(f"Benutzer {email} angelegt.")

elif cmd == "remove":
    email = input("E-Mail: ").strip().lower()
    users = load()
    if email not in users:
        print(f"Benutzer {email} nicht gefunden.")
        sys.exit(1)
    del users[email]
    save(users)
    print(f"Benutzer {email} entfernt.")

elif cmd == "list":
    users = load()
    if not users:
        print("Keine Benutzer angelegt.")
    else:
        print(f"{len(users)} Benutzer:")
        for e in sorted(users):
            print(f"  {e}")

elif cmd == "passwd":
    email = input("E-Mail: ").strip().lower()
    users = load()
    if email not in users:
        print(f"Benutzer {email} nicht gefunden.")
        sys.exit(1)
    password = getpass.getpass("Neues Passwort: ")
    if len(password) < 8:
        print("Fehler: Passwort muss mindestens 8 Zeichen haben.")
        sys.exit(1)
    users[email] = hash_password(password)
    save(users)
    print(f"Passwort für {email} geändert.")

else:
    print(__doc__)
