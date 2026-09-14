import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session

load_dotenv()

from database import Base, engine, get_db
from models import User, Book, Loan, Role, ReadingLog
from auth import hash_password, get_current_user
from routers import auth as auth_router
from routers import books as books_router
from routers import members as members_router
from routers import loans as loans_router
from routers import reading as reading_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Management System")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router.router)
app.include_router(books_router.router)
app.include_router(members_router.router)
app.include_router(loans_router.router)
app.include_router(reading_router.router)


@app.exception_handler(StarletteHTTPException)
def redirect_unauthenticated(request: Request, exc: StarletteHTTPException):
    # require_login/require_staff raise 303 with a Location header to send
    # unauthenticated or unauthorized users to the login page.
    location = exc.headers.get("Location") if exc.headers else None
    if location:
        return RedirectResponse(location, status_code=303)
    return HTMLResponse(f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>", status_code=exc.status_code)


@app.on_event("startup")
def seed_admins():
    """Creates three initial staff (admin) accounts on first run, so there's
    never a single point of failure for library administration. Change these
    passwords immediately after first login."""
    db: Session = next(get_db())
    try:
        if db.query(User).count() == 0:
            default_admins = [
                {"name": "Head Librarian", "username": "admin1", "password": "admin123"},
                {"name": "Assistant Librarian", "username": "admin2", "password": "admin123"},
                {"name": "Circulation Staff", "username": "admin3", "password": "admin123"},
            ]
            for a in default_admins:
                db.add(User(
                    name=a["name"],
                    username=a["username"],
                    password_hash=hash_password(a["password"]),
                    role=Role.STAFF,
                ))
            db.commit()
            print("Created 3 initial staff accounts: admin1/admin2/admin3 (password: admin123)")
            print("IMPORTANT: change these passwords after first login.")
    finally:
        db.close()
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    total_books = db.query(Book).count()
    total_copies = sum(b.total_copies for b in db.query(Book).all())
    available_copies = sum(b.available_copies for b in db.query(Book).all())

    if user.is_staff:
        active_loans = db.query(Loan).filter(Loan.return_date.is_(None)).count()
        total_members = db.query(User).filter(User.role == Role.MEMBER).count()
        my_loans = []
        my_hours = None
        my_books_read = None
    else:
        active_loans = 0
        total_members = 0
        my_loans = db.query(Loan).filter(Loan.member_id == user.id, Loan.return_date.is_(None)).all()
        my_logs = db.query(ReadingLog).filter(ReadingLog.member_id == user.id).all()
        my_hours = sum(l.hours for l in my_logs)
        my_books_read = len({l.book_id for l in my_logs if l.finished})

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_books": total_books,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "active_loans": active_loans,
            "total_members": total_members,
            "my_loans": my_loans,
            "my_hours": my_hours,
            "my_books_read": my_books_read,
        },
    )
