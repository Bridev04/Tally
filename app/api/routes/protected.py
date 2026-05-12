from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User


router = APIRouter(prefix="/protected", tags=["protected"])


@router.get("/ping")
def protected_ping(current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
    # Future app routers should depend on get_current_user before accessing user data.
    return {"status": "ok", "user_id": str(current_user.id)}
