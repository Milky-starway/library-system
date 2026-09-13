"""
Bulk-import books from a CSV file into the library database.

Usage:
    python seed_books.py books.csv

CSV columns required (header row must match exactly):
    title,author,isbn,category,total_copies

- isbn and category can be left blank per row.
- total_copies must be a whole number (defaults to 1 if blank).
- Books are matched by ISBN: if a book with that ISBN already exists,
  its total_copies/available_copies is increased instead of creating
  a duplicate. Books with no ISBN are always added as new.
"""
import csv
import sys

from database import SessionLocal
from models import Book


def seed_books(csv_path: str):
    db = SessionLocal()
    added, updated, skipped = 0, 0, 0
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"title", "author"}
            if not required.issubset(set(reader.fieldnames or [])):
                print(f"ERROR: CSV must have at least these columns: {required}")
                print(f"Found columns: {reader.fieldnames}")
                sys.exit(1)

            for i, row in enumerate(reader, start=2):  # row 1 is the header
                title = (row.get("title") or "").strip()
                author = (row.get("author") or "").strip()
                isbn = (row.get("isbn") or "").strip() or None
                category = (row.get("category") or "").strip() or None
                copies_raw = (row.get("total_copies") or "").strip()

                if not title or not author:
                    print(f"Row {i}: skipped (missing title or author)")
                    skipped += 1
                    continue

                try:
                    total_copies = int(copies_raw) if copies_raw else 1
                except ValueError:
                    print(f"Row {i}: skipped (total_copies '{copies_raw}' is not a whole number)")
                    skipped += 1
                    continue

                existing = db.query(Book).filter(Book.isbn == isbn).first() if isbn else None
                if existing:
                    existing.total_copies += total_copies
                    existing.available_copies += total_copies
                    updated += 1
                else:
                    db.add(Book(
                        title=title, author=author, isbn=isbn,
                        category=category, total_copies=total_copies,
                        available_copies=total_copies,
                    ))
                    added += 1

        db.commit()
        print(f"\nDone. Added {added} new book(s), updated {updated} existing, skipped {skipped}.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python seed_books.py <path-to-csv>")
        sys.exit(1)
    seed_books(sys.argv[1])


