import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, NoReturn

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.constants.errors import (
    AUTH_ERROR_ADMIN_REQUIRED,
    AUTH_ERROR_CHANGE_PASSWORD,
    AUTH_ERROR_CREATE_USER_SERVER,
    AUTH_ERROR_INVALID_CREDENTIALS,
    AUTH_ERROR_INVALID_OR_EXPIRED_TOKEN,
    AUTH_ERROR_INVALID_TOKEN,
    AUTH_ERROR_NOT_AUTHENTICATED,
    AUTH_ERROR_PARTNER_CITY_ADMIN_USER,
    AUTH_ERROR_PARTNER_CITY_UPDATE,
    AUTH_ERROR_UPDATE_CONTACT,
    AUTH_ERROR_USER_NOT_FOUND,
    AUTH_ERROR_USERNAME_EXISTS,
)
from app.constants.feature_flags import auth_disabled
from app.database import SessionLocal, User, UserActionJournal, get_db, get_db_optional
from app.schemas import (
    LoginRequest,
    TokenResponse,
    UserActionJournalResponse,
    UserContactUpdate,
    UserCreate,
    UserPartnerCityUpdate,
    UserPasswordUpdate,
    UserResponse,
)
from app.stub_alert_settings import get_stub_alert_settings

SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-production-use-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

BCRYPT_MAX_PASSWORD_BYTES = 72
security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _stub_admin_user() -> User:
    s = get_stub_alert_settings()
    pluv = s.get("alert_pluvial_enabled", False)
    fluv = s.get("alert_fluvial_enabled", False)
    heat = s.get("alert_heatwave_enabled", False)
    snow = s.get("alert_snow_enabled", False)
    any_on = pluv or fluv or heat or snow
    return User(
        id=0,
        username=os.environ.get("AUTH_STUB_USERNAME", "dev"),
        hashed_password="",
        is_admin=True,
        email=os.environ.get("AUTH_STUB_EMAIL", "dev@example.com"),
        phone=os.environ.get("AUTH_STUB_PHONE") or None,
        alert_threshold_flood_pct=s.get("alert_threshold_pluvial_pct", 50.0),
        alerts_enabled=any_on,
        alert_pluvial_enabled=pluv,
        alert_fluvial_enabled=fluv,
        alert_heatwave_enabled=heat,
        alert_snow_enabled=snow,
        alert_threshold_pluvial_pct=s.get("alert_threshold_pluvial_pct", 50.0),
        alert_threshold_fluvial_pct=s.get("alert_threshold_fluvial_pct", 50.0),
        alert_threshold_heatwave_humidex=s.get(
            "alert_threshold_heatwave_humidex", 41.0
        ),
        alert_threshold_snow_pct=s.get("alert_threshold_snow_pct", 20.0),
        alert_via_sms=s.get("alert_via_sms", True),
        alert_via_email=s.get("alert_via_email", False),
        alert_frequency_hours=s.get("alert_frequency_hours", 4),
        last_flood_alert_sent_at=s.get("last_pluvial_alert_sent_at"),
        last_pluvial_alert_sent_at=s.get("last_pluvial_alert_sent_at"),
        last_fluvial_alert_sent_at=s.get("last_fluvial_alert_sent_at"),
        last_heatwave_alert_sent_at=s.get("last_heatwave_alert_sent_at"),
        last_snow_alert_sent_at=s.get("last_snow_alert_sent_at"),
        partner_city=None,
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(user_id: int, db: Session) -> User:
    if auth_disabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=AUTH_ERROR_USER_NOT_FOUND,
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=AUTH_ERROR_USER_NOT_FOUND,
        )
    return user


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        email=user.email,
        phone=user.phone,
        partner_city=user.partner_city,
    )


def _unauthorized(detail: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session | None, Depends(get_db_optional)],
) -> User:
    if auth_disabled():
        return _stub_admin_user()
    if not credentials or not credentials.credentials:
        _unauthorized(AUTH_ERROR_NOT_AUTHENTICATED)
    payload = decode_token(credentials.credentials)
    if not payload:
        _unauthorized(AUTH_ERROR_INVALID_OR_EXPIRED_TOKEN)
    username = payload.get("sub")
    if not username:
        _unauthorized(AUTH_ERROR_INVALID_TOKEN)
    user = get_user_by_username(db, username)
    if not user:
        _unauthorized(AUTH_ERROR_USER_NOT_FOUND)
    return user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if auth_disabled():
        return _stub_admin_user()
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=AUTH_ERROR_ADMIN_REQUIRED,
        )
    return current_user


def ensure_admin_user() -> None:
    if auth_disabled():
        return
    db = SessionLocal()
    try:
        if db.query(User).filter(User.is_admin).first():
            return
        admin_username = os.environ.get("ADMIN_USERNAME", "admin")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
        if not admin_username or not admin_password:
            return
        admin = User(
            username=admin_username,
            hashed_password=get_password_hash(admin_password),
            is_admin=True,
            partner_city=None,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    if auth_disabled():
        access_token = create_access_token(data={"sub": "dev"})
        return TokenResponse(access_token=access_token)
    user = get_user_by_username(db, body.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_ERROR_INVALID_CREDENTIALS,
        )
    pw_ok = await asyncio.to_thread(
        verify_password, body.password, user.hashed_password
    )
    if not pw_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AUTH_ERROR_INVALID_CREDENTIALS,
        )
    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def auth_me(current_user: Annotated[User, Depends(get_current_user)]):
    return user_to_response(current_user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    users = db.query(User).order_by(User.username).all()
    return [user_to_response(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    if get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=AUTH_ERROR_USERNAME_EXISTS,
        )
    try:
        hashed = await asyncio.to_thread(get_password_hash, body.password)
        user = User(
            username=body.username,
            hashed_password=hashed,
            is_admin=False,
            email=body.email,
            phone=body.phone.strip(),
            partner_city=body.partner_city,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_response(user)
    except Exception as e:
        db.rollback()
        print(f"[create_user] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=AUTH_ERROR_CREATE_USER_SERVER,
        ) from e


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    user = get_user_by_id(user_id, db)
    return user_to_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user_password(
    user_id: int,
    body: UserPasswordUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    user = get_user_by_id(user_id, db)
    try:
        user.hashed_password = await asyncio.to_thread(get_password_hash, body.password)
        db.commit()
        db.refresh(user)
        return user_to_response(user)
    except Exception as e:
        db.rollback()
        print(f"[update_user_password] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=AUTH_ERROR_CHANGE_PASSWORD,
        ) from e


@router.patch("/users/{user_id}/contact", response_model=UserResponse)
async def update_user_contact(
    user_id: int,
    body: UserContactUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    user = get_user_by_id(user_id, db)
    try:
        user.email = body.email
        user.phone = body.phone
        db.commit()
        db.refresh(user)
        return user_to_response(user)
    except Exception as e:
        db.rollback()
        print(f"[update_user_contact] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=AUTH_ERROR_UPDATE_CONTACT,
        ) from e


@router.patch("/users/{user_id}/partner-city", response_model=UserResponse)
async def update_user_partner_city(
    user_id: int,
    body: UserPartnerCityUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    user = get_user_by_id(user_id, db)
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=AUTH_ERROR_PARTNER_CITY_ADMIN_USER,
        )
    try:
        user.partner_city = body.partner_city
        db.commit()
        db.refresh(user)
        return user_to_response(user)
    except Exception as e:
        db.rollback()
        print(f"[update_user_partner_city] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=AUTH_ERROR_PARTNER_CITY_UPDATE,
        ) from e


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
):
    user = get_user_by_id(user_id, db)
    db.delete(user)
    db.commit()
    return None


@router.get("/users/{user_id}/logs", response_model=list[UserActionJournalResponse])
async def get_user_logs(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    date: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    get_user_by_id(user_id, db)

    query = db.query(UserActionJournal).filter(UserActionJournal.user_id == user_id)
    if date:
        query = query.filter(UserActionJournal.log_date == date)
    logs = query.order_by(UserActionJournal.id.desc()).limit(limit).all()
    return logs
