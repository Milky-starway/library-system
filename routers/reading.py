import csv
import io

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import ReadingLog, Book, User, Role
from auth import require_login, require_staff

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def member_stats(db: Session, member_id: int):
    logs = db.query(ReadingLog).filter(ReadingLog.member_id == member_id).all()
    total_hours = sum(l.hours for l in logs)
    books_finished = {l.book_id for l in logs if l.finished}

    # Group by book: total hours per title, and whether it's been finished
    by_book = {}
    for l in logs:
        entry = by_book.setdefault(l.book_id, {"book": l.book, "hours": 0, "finished": False})
        entry["hours"] += l.hours
        if l.finished:
            entry["finished"] = True
    books_breakdown = sorted(by_book.values(), key=lambda b: b["book"].title)

    return {
        "logs": sorted(logs, key=lambda l: l.date, reverse=True),
        "total_hours": total_hours,
        "books_read_count": len(books_finished),
        "books_breakdown": books_breakdown,
    }


@router.get("/reading/export.csv")
def export_reading_csv(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    logs = db.query(ReadingLog).join(User, ReadingLog.member_id == User.id).all()

    # Sort by member name, then most recent session first within each member
    logs_sorted = sorted(logs, key=lambda l: (l.member.name, -l.date.timestamp()))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Member Name", "Member Email", "Book Title", "Date", "Hours", "Finished"])

    last_member_id = None
    for l in logs_sorted:
        is_new_member = l.member_id != last_member_id
        writer.writerow([
            l.member.name if is_new_member else "",
            l.member.email if is_new_member else "",
            l.book.title,
            l.date.strftime("%Y-%m-%d"), l.hours, "Yes" if l.finished else "No",
        ])
        last_member_id = l.member_id

    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reading_activity.csv"},
    )


@router.get("/reading", response_class=HTMLResponse)
def reading_history(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if user.is_staff:
        members = db.query(User).filter(User.role == Role.MEMBER).order_by(User.name).all()
        member_summaries = [{"member": m, **member_stats(db, m.id)} for m in members]
        return templates.TemplateResponse(
            "reading_list_staff.html",
            {"request": request, "user": user, "member_summaries": member_summaries},
        )
    else:
        stats = member_stats(db, user.id)
        return templates.TemplateResponse(
            "reading_list.html", {"request": request, "user": user, **stats}
        )


@router.get("/reading/member/{member_id}", response_class=HTMLResponse)
def member_reading_detail(member_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    member = db.query(User).filter(User.id == member_id).first()
    stats = member_stats(db, member_id)
    return templates.TemplateResponse(
        "reading_detail.html", {"request": request, "user": user, "member": member, **stats}
    )


@router.get("/reading/new", response_class=HTMLResponse)
def new_reading_log_form(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    books = db.query(Book).order_by(Book.title).all()
    members = db.query(User).filter(User.role == Role.MEMBER).order_by(User.name).all()
    return templates.TemplateResponse(
        "reading_form.html",
        {"request": request, "user": user, "books": books, "members": members, "error": None},
    )


@router.post("/reading/new", response_class=HTMLResponse)
def new_reading_log_submit(
    request: Request,
    member_id: int = Form(...),
    book_id: int = Form(...),
    hours: float = Form(...),
    finished: str = Form(None),
    db: Session = Depends(get_db),
):
    user = require_staff(request, db)
    log = ReadingLog(member_id=member_id, book_id=book_id, hours=hours, finished=bool(finished))
    db.add(log)
    db.commit()
    return RedirectResponse("/reading", status_code=303)