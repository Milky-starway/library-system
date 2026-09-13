import enum
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Enum, Boolean, Float
)
from sqlalchemy.orm import relationship

from database import Base


class Role(str, enum.Enum):
    STAFF = "staff"
    MEMBER = "member"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.MEMBER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    loans = relationship("Loan", back_populates="member")

    @property
    def is_staff(self):
        return self.role == Role.STAFF


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, nullable=True)
    category = Column(String, nullable=True)
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    loans = relationship("Loan", back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checkout_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)

    book = relationship("Book", back_populates="loans")
    member = relationship("User", back_populates="loans")

    @property
    def is_returned(self):
        return self.return_date is not None

    @property
    def is_overdue(self):
        return not self.is_returned and datetime.utcnow() > self.due_date

    @staticmethod
    def default_due_date():
        return datetime.utcnow() + timedelta(days=14)


class ReadingLog(Base):
    """Records a member reading a book in the library (in-house reading,
    separate from checkout/return), so hours and books-read can be tracked
    even when a book never leaves the building."""

    __tablename__ = "reading_logs"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    hours = Column(Float, nullable=False)
    finished = Column(Boolean, default=True)  # counts toward "books read" if true

    member = relationship("User", backref="reading_logs")
    book = relationship("Book", backref="reading_logs")
