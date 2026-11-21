
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database.database import get_session
from app.database.models import User
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.services.auth_dependencies import get_current_user


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


@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
