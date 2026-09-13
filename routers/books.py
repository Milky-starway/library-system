from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import Book
from auth import require_login, require_staff

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/books", response_class=HTMLResponse)
def list_books(request: Request, q: str = "", db: Session = Depends(get_db)):
    user = require_login(request, db)
    query = db.query(Book)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like)))
    books = query.order_by(Book.title).all()
    return templates.TemplateResponse(
        "books_list.html", {"request": request, "user": user, "books": books, "q": q}
    )


@router.get("/books/new", response_class=HTMLResponse)
def new_book_form(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    return templates.TemplateResponse(
        "book_form.html", {"request": request, "user": user, "book": None, "error": None}
    )


@router.post("/books/new", response_class=HTMLResponse)
def new_book_submit(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(""),
    category: str = Form(""),
    total_copies: int = Form(1),
    db: Session = Depends(get_db),
):
    user = require_staff(request, db)
    book = Book(
        title=title,
        author=author,
        isbn=isbn or None,
        category=category or None,
        total_copies=total_copies,
        available_copies=total_copies,
    )
    db.add(book)
    db.commit()
    return RedirectResponse("/books", status_code=303)


@router.get("/books/{book_id}/edit", response_class=HTMLResponse)
def edit_book_form(book_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    book = db.query(Book).filter(Book.id == book_id).first()
    return templates.TemplateResponse(
        "book_form.html", {"request": request, "user": user, "book": book, "error": None}
    )


@router.post("/books/{book_id}/edit", response_class=HTMLResponse)
def edit_book_submit(
    book_id: int,
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(""),
    category: str = Form(""),
    total_copies: int = Form(1),
    db: Session = Depends(get_db),
):
    user = require_staff(request, db)
    book = db.query(Book).filter(Book.id == book_id).first()
    on_loan = book.total_copies - book.available_copies
    book.title = title
    book.author = author
    book.isbn = isbn or None
    book.category = category or None
    book.total_copies = total_copies
    book.available_copies = max(total_copies - on_loan, 0)
    db.commit()
    return RedirectResponse("/books", status_code=303)


@router.post("/books/{book_id}/delete")
def delete_book(book_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    book = db.query(Book).filter(Book.id == book_id).first()
    if book:
        db.delete(book)
        db.commit()
    return RedirectResponse("/books", status_code=303)
