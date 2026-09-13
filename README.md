# Library Management System

FastAPI + SQLAlchemy + server-rendered HTML (Jinja2). SQLite by default, switch to
PostgreSQL/MySQL by changing one line in `.env`.

## Where to start

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Set up your environment file**
   ```
   cp .env.example .env
   ```
   Leave `DATABASE_URL` as-is for SQLite (zero setup), or point it at Postgres/MySQL.

3. **Run it**
   ```
   uvicorn main:app --reload
   ```
   Open http://127.0.0.1:8000

4. **Log in** with one of the three seeded staff accounts (created automatically on
   first run — change these passwords right away):
   - admin1@library.local / admin123
   - admin2@library.local / admin123
   - admin3@library.local / admin123

5. **From there**, as staff you can: add books (`Books` → `+ Add book`), add more
   staff or members (`Members`), check books out to members and mark returns
   (`Loans`), and log in-library reading sessions (`Reading` → `+ Log a reading
   session`) — this is what feeds each member's "books read" and "hours read" stats.

   Members can also self-register at `/register` (always as a member — staff
   accounts are only created by existing staff).

## Project layout
```
main.py            entrypoint, dashboard, admin seeding
models.py          User, Book, Loan, ReadingLog
auth.py            password hashing, session helpers
database.py        SQLAlchemy engine/session
routers/
  auth.py          login, logout, register
  books.py         catalog CRUD + search
  members.py       staff manage members/staff
  loans.py         checkout / return
  reading.py       log & view reading history/stats
templates/         Jinja2 pages
static/css/        stylesheet
```

## Notes
- Due date on checkout is fixed at 14 days — change `Loan.default_due_date()` in
  `models.py` if you want it configurable.
- Only staff can log reading sessions and record checkouts/returns — members are
  read-only on their own history.
