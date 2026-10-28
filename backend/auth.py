"""SQLite-backed accounts, Argon2 password hashes, and opaque cookie sessions."""
import hashlib
from functools import lru_cache
import os
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlparse
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, root_validator, validator
from pwdlib import PasswordHash
from rate_limiter import limiter
from sqlalchemy import DateTime, ForeignKey, String, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session as DBSession, mapped_column

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

router = APIRouter(prefix="/auth", tags=["authentication"])
password_hasher = PasswordHash.recommended()
SESSION_COOKIE = "vistaar_session"
SESSION_DAYS = 14
RESET_MINUTES = 30
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def database_url() -> str:
    configured = os.getenv("VISTAAR_AUTH_DB", "vistaar_auth.sqlite3")
    if "://" in configured:
        return configured
    path = Path(configured)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254, collation="NOCASE"), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _now())


class AuthSession(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: _now())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


@lru_cache(maxsize=8)
def _engine_for(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    return engine


def get_db():
    with DBSession(_engine_for(database_url())) as db:
        yield db


def init_auth_db() -> None:
    Base.metadata.create_all(bind=_engine_for(database_url()))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cookie_secure() -> bool:
    configured = os.getenv("VISTAAR_COOKIE_SECURE")
    production = os.getenv("VISTAAR_ENV", "development").lower() in {"production", "prod"}
    if configured is not None:
        secure = configured.lower() == "true"
        if production and not secure:
            raise RuntimeError("VISTAAR_COOKIE_SECURE must be true in production")
        return secure
    return production


def _cookie_samesite() -> str:
    value = os.getenv("VISTAAR_COOKIE_SAMESITE", "lax").lower()
    if value not in {"lax", "strict", "none"}:
        raise RuntimeError("VISTAAR_COOKIE_SAMESITE must be lax, strict, or none")
    if value == "none" and not _cookie_secure():
        raise RuntimeError("SameSite=None requires VISTAAR_COOKIE_SECURE=true")
    return value


def allowed_frontend_origins() -> list[str]:
    origins = {
        item.strip().rstrip("/").lower()
        for item in os.getenv("VISTAAR_CORS_ORIGINS", "").split(",")
        if item.strip()
    }
    is_production = os.getenv("VISTAAR_ENV", "development").lower() in {"production", "prod"}
    if not is_production:
        # Vite's proxy rewrites Host to the backend target while the browser Origin
        # remains the local frontend origin. Trust only the project's known dev ports.
        origins.update({"http://localhost:5173", "http://127.0.0.1:5173"})
    return sorted(origins)


def _verify_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    origin_host = urlparse(origin).netloc.lower()
    request_host = request.headers.get("host", "").lower()
    allowed = set(allowed_frontend_origins())
    if origin_host != request_host and origin.rstrip("/").lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed. Configure VISTAAR_CORS_ORIGINS for the frontend origin.",
        )


def _public_user(row: User) -> dict:
    return {"id": row.id, "fullName": row.full_name, "email": row.email}


class RegisterInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @root_validator(pre=True)
    def accept_name_aliases(cls, values):
        if isinstance(values, dict) and "full_name" not in values:
            values["full_name"] = values.get("name") or values.get("fullName")
        return values

    @validator("full_name")
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @validator("email")
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class ForgotPasswordInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @validator("email")
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value


class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=8, max_length=128)


def _set_session(db: DBSession, response: Response, user_id: int) -> None:
    raw_token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(days=SESSION_DAYS)
    db.add(AuthSession(token_hash=_hash_token(raw_token), user_id=user_id, expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        max_age=SESSION_DAYS * 24 * 60 * 60,
        path="/",
    )


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> dict:
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        _verify_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.get(AuthSession, _hash_token(token))
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    return _public_user(user)


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, response: Response, payload: RegisterInput = Body(...), db: DBSession = Depends(get_db)):
    _verify_origin(request)
    password_hash = password_hasher.hash(payload.password)
    user = User(full_name=payload.full_name, email=payload.email, password_hash=password_hash)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists") from exc
    _set_session(db, response, user.id)
    return {"user": _public_user(user)}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, response: Response, payload: LoginInput = Body(...), db: DBSession = Depends(get_db)):
    _verify_origin(request)
    row = db.scalar(select(User).where(User.email == payload.email))
    # Run a hash verification for unknown emails too, limiting account enumeration timing.
    if row is None:
        password_hasher.hash("invalid-login-placeholder")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not password_hasher.verify(payload.password, row.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    _set_session(db, response, row.id)
    return {"user": _public_user(row)}


@router.get("/me")
def current_user(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.post("/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    _verify_origin(request)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = db.get(AuthSession, _hash_token(token))
        if session is not None:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite=_cookie_samesite(), secure=_cookie_secure())
    return {"message": "Signed out"}


def _smtp_configured() -> bool:
    return all(os.getenv(key) for key in ("VISTAAR_SMTP_HOST", "VISTAAR_SMTP_FROM"))


def _send_reset_email(email: str, token: str) -> None:
    host = os.environ["VISTAAR_SMTP_HOST"]
    port = int(os.getenv("VISTAAR_SMTP_PORT", "587"))
    username = os.getenv("VISTAAR_SMTP_USERNAME")
    password = os.getenv("VISTAAR_SMTP_PASSWORD")
    frontend = os.getenv("VISTAAR_FRONTEND_URL", "http://localhost:5173").rstrip("/")
    message = EmailMessage()
    message["Subject"] = "Reset your VISTAAR password"
    message["From"] = os.environ["VISTAAR_SMTP_FROM"]
    message["To"] = email
    message.set_content(f"Reset your VISTAAR password using this link (valid for 30 minutes):\n\n{frontend}/reset-password?token={token}\n")
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls(context=ssl.create_default_context())
        if username:
            server.login(username, password or "")
        server.send_message(message)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: ForgotPasswordInput = Body(...), db: DBSession = Depends(get_db)):
    _verify_origin(request)
    if not _smtp_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password recovery email is not configured. Contact the VISTAAR administrator.")
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
        db.add(PasswordReset(token_hash=_hash_token(raw_token), user_id=user.id, expires_at=_now() + timedelta(minutes=RESET_MINUTES)))
        db.commit()
        try:
            _send_reset_email(payload.email, raw_token)
        except Exception as exc:
            db.query(PasswordReset).filter(PasswordReset.token_hash == _hash_token(raw_token)).delete()
            db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not send recovery email. Try again later.") from exc
    return {"message": "If an account exists for that address, recovery instructions have been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, response: Response, payload: ResetPasswordInput = Body(...), db: DBSession = Depends(get_db)):
    _verify_origin(request)
    token_hash = _hash_token(payload.token)
    reset = db.get(PasswordReset, token_hash)
    expires_at = reset.expires_at if reset is not None else None
    if expires_at is None or (expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at) <= _now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link is invalid or expired")
    user = db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link is invalid or expired")
    user.password_hash = password_hasher.hash(payload.password)
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite=_cookie_samesite(), secure=_cookie_secure())
    return {"message": "Password reset. You can now sign in."}


@router.on_event("startup")
def _startup() -> None:
    _cookie_samesite()
    init_auth_db()
