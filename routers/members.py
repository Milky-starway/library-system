import csv
import io

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User, Role
from auth import require_staff, hash_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/members/export.csv")
def export_members_csv(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    members = db.query(User).order_by(User.name).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Name", "Username", "Email", "Role", "Account Created", "Last Login"])
    for m in members:
        writer.writerow([
            m.name, m.username, m.email or "",
            m.role.value,
            m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
            m.last_login.strftime("%Y-%m-%d %H:%M") if m.last_login else "Never logged in",
        ])
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=members_and_logins.csv"},
    )


@router.get("/members", response_class=HTMLResponse)
def list_members(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    members = db.query(User).order_by(User.name).all()
    return templates.TemplateResponse(
        "members_list.html", {"request": request, "user": user, "members": members}
    )


@router.get("/members/new", response_class=HTMLResponse)
def new_member_form(request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    return templates.TemplateResponse(
        "member_form.html", {"request": request, "user": user, "error": None}
    )


@router.post("/members/new", response_class=HTMLResponse)
def new_member_submit(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
    role: str = Form("member"),
    db: Session = Depends(get_db),
):
    user = require_staff(request, db)
    username = username.strip().lower()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return templates.TemplateResponse(
            "member_form.html",
            {"request": request, "user": user, "error": "That username is already taken"},
        )
    new_user = User(
        name=name,
        username=username,
        email=email.strip() or None,
        password_hash=hash_password(password),
        role=Role.STAFF if role == "staff" else Role.MEMBER,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse("/members", status_code=303)


@router.post("/members/{member_id}/delete")
def delete_member(member_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_staff(request, db)
    if member_id == user.id:
        return RedirectResponse("/members", status_code=303)
    member = db.query(User).filter(User.id == member_id).first()
    if member:
        db.delete(member)
        db.commit()
    return RedirectResponse("/members", status_code=303)