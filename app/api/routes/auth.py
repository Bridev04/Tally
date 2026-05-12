from datetime import timedelta
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.audit import create_audit_log


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
auth_rate_limiter: InMemoryRateLimiter | None = None


def get_auth_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global auth_rate_limiter
    if (
        auth_rate_limiter is None
        or auth_rate_limiter.limit != settings.auth_rate_limit_requests
        or auth_rate_limiter.window_seconds != settings.auth_rate_limit_window_seconds
    ):
        auth_rate_limiter = InMemoryRateLimiter(
            limit=settings.auth_rate_limit_requests,
            window_seconds=settings.auth_rate_limit_window_seconds,
        )
    return auth_rate_limiter


def check_auth_rate_limit(
    request: Request,
    limiter: Annotated[InMemoryRateLimiter, Depends(get_auth_rate_limiter)],
) -> None:
    limiter.check(key=f"{request.url.path}:{get_client_ip(request)}")


def check_auth_identity_rate_limit(
    *,
    email: str,
    request: Request,
    limiter: InMemoryRateLimiter,
) -> None:
    limiter.check(key=f"{request.url.path}:email:{email.lower()}")


def build_token_response(*, user: User, settings: Settings) -> TokenResponse:
    token = create_access_token(
        user_id=user.id,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_auth_rate_limit)],
)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_auth_rate_limiter)],
) -> TokenResponse:
    check_auth_identity_rate_limit(email=payload.email, request=request, limiter=limiter)
    existing_user = session.exec(select(User).where(User.email == payload.email)).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    create_audit_log(session=session, user_id=user.id, action="auth.registered")
    session.commit()
    session.refresh(user)
    logger.info("User registered", extra={"user_id": str(user.id)})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return build_token_response(user=user, settings=settings)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(check_auth_rate_limit)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_auth_rate_limiter)],
) -> TokenResponse:
    check_auth_identity_rate_limit(email=payload.email, request=request, limiter=limiter)
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    create_audit_log(session=session, user_id=user.id, action="auth.logged_in")
    session.commit()
    session.refresh(user)
    logger.info("User logged in", extra={"user_id": str(user.id)})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return build_token_response(user=user, settings=settings)


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
