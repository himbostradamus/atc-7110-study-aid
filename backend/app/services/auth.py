"""
Minimal auth shim for the reorganized snapshot.

The original authentication module was not included in the extracted files.
Protected endpoints now fail explicitly until real auth is added back.
For local development, an opt-in bypass can synthesize a user from the DB.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, status

from ..models.orm import User, UserRole
from .db import SessionLocal


def get_current_user() -> User:
    if os.getenv("ATC_DEV_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}:
        email = os.getenv("ATC_DEV_USER_EMAIL", "dev@local")
        try:
            with SessionLocal() as db:
                user = db.query(User).filter(User.email == email).first()
                if user:
                    return user

                user = User(
                    email=email,
                    password_hash="dev-auth-bypass",
                    first_name="Dev",
                    last_name="User",
                    role=UserRole.admin,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication is not wired in this snapshot yet.",
    )
