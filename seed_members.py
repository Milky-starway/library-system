"""
Bulk-import members (or staff) from a CSV file into the library database.

Usage:
    python seed_members.py members.csv

CSV columns required (header row must match exactly):
    name,email,password,role

- role must be either "member" or "staff" (defaults to "member" if blank).
- If an email already exists, that row is skipped (no duplicates, no
  overwriting of an existing account's password).
"""
import csv
import sys

from database import SessionLocal
from models import User, Role
from auth import hash_password


def seed_members(csv_path: str):
    db = SessionLocal()
    added, skipped = 0, 0
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"name", "email", "password"}
            if not required.issubset(set(reader.fieldnames or [])):
                print(f"ERROR: CSV must have at least these columns: {required}")
                print(f"Found columns: {reader.fieldnames}")
                sys.exit(1)

            for i, row in enumerate(reader, start=2):  # row 1 is the header
                name = (row.get("name") or "").strip()
                email = (row.get("email") or "").strip().lower()
                password = (row.get("password") or "").strip()
                role_raw = (row.get("role") or "").strip().lower()

                if not name or not email or not password:
                    print(f"Row {i}: skipped (missing name, email, or password)")
                    skipped += 1
                    continue

                if db.query(User).filter(User.email == email).first():
                    print(f"Row {i}: skipped ({email} already exists)")
                    skipped += 1
                    continue

                role = Role.STAFF if role_raw == "staff" else Role.MEMBER
                db.add(User(
                    name=name, email=email,
                    password_hash=hash_password(password),
                    role=role,
                ))
                added += 1

        db.commit()
        print(f"\nDone. Added {added} new person/people, skipped {skipped}.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python seed_members.py <path-to-csv>")
        sys.exit(1)
    seed_members(sys.argv[1])
