
import logging
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlmodel import Session, select

from app.database.database import get_session
from app.database.models import User
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleLoginRequest,
    UserResponse,
    TokenResponse,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.services.auth_dependencies import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    request: UserRegisterRequest,
    session: Session = Depends(get_session)
):
    email = str(request.email).strip().lower()

    statement = select(User).where(User.email == email)
    existing_user = session.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    user = User(
        email=email,
        password_hash=hash_password(request.password)
    )

    try:
        session.add(user)
        session.commit()
        session.refresh(user)

    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account registration failed."
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    request: UserLoginRequest,
    session: Session = Depends(get_session)
):
    email = str(request.email).strip().lower()

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if user is None or not verify_password(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post(
    "/google",
    response_model=TokenResponse
)
def google_login(
    request: GoogleLoginRequest,
    session: Session = Depends(get_session)
):
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication is not configured."
        )

    try:
        google_user = id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            client_id
        )

    except (ValueError, GoogleAuthError) as error:
        logger.exception(
            "Google ID token verification failed: %s",
            type(error).__name__
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token."
        )

    email = google_user.get("email")

    if (
        not email
        or str(google_user.get("email_verified")).lower() != "true"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A verified Google email is required."
        )

    email = email.strip().lower()

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(
                secrets.token_urlsafe(32)
            )
        )

        try:
            session.add(user)
            session.commit()
            session.refresh(user)

        except Exception:
            session.rollback()

            # Handle possible simultaneous account creation.
            user = session.exec(statement).first()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google account creation failed."
                )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
