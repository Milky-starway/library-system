from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Loan, Book, User, Role
from auth import require_login, require_staff

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/loans", response_class=HTMLResponse)
def list_loans(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    query = db.query(Loan)
    if not user.is_staff:
        query = query.filter(Loan.member_id == user.id)
    loans = query.order_by(Loan.checkout_date.desc()).all()
    return templates.TemplateResponse(
        "loans_list.html", {"request": request, "user": user, "loans": loans, "now": datetime.utcnow()}
    )


@router.get("/loans/checkout", response_class=HTMLResponse)
def checkout_form(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    books = db.query(Book).filter(Book.available_copies > 0).order_by(Book.title).all()
    members = db.query(User).filter(User.role == Role.MEMBER).order_by(User.name).all()
    return templates.TemplateResponse(
        "checkout_form.html",
        {"request": request, "user": user, "books": books, "members": members, "error": None},
    )


@router.post("/loans/checkout", response_class=HTMLResponse)
def checkout_submit(
    request: Request,
    book_id: int = Form(...),
    member_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_staff(request, db)
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or book.available_copies < 1:
        books = db.query(Book).filter(Book.available_copies > 0).order_by(Book.title).all()
        members = db.query(User).filter(User.role == Role.MEMBER).order_by(User.name).all()
        return templates.TemplateResponse(
            "checkout_form.html",
            {
                "request": request, "user": user, "books": books, "members": members,
                "error": "That book has no available copies.",
            },
        )
    loan = Loan(book_id=book.id, member_id=member_id, due_date=Loan.default_due_date())
    book.available_copies -= 1
    db.add(loan)
    db.commit()
    return RedirectResponse("/loans", status_code=303)


@router.post("/loans/{loan_id}/return")
def return_book(loan_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if loan and not loan.return_date:
        loan.return_date = datetime.utcnow()
        loan.book.available_copies += 1
        db.commit()
    return RedirectResponse("/loans", status_code=303)
