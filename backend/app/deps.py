from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .db import User, get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def token_user(credentials, db):
    payload = decode_token(credentials.credentials) if credentials else None
    user = db.get(User, payload['sub']) if payload else None
    return user if user and user.token_version == payload.get('tv', 0) else None


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    user = token_user(credentials, db)
    if not user:
        raise HTTPException(401, '登录已过期，请重新登录')
    return user


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    # Public pages ignore stale tokens instead of failing; they only personalise likedByMe.
    return token_user(credentials, db)


def is_admin(user):
    return bool(user) and user.phone in settings.admin_phones


def admin_user(user: User = Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403, '需要管理员权限')
    return user
