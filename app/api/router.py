from fastapi import APIRouter

from app.api.routes import auth, imports, protected, transactions


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(imports.router)
api_router.include_router(protected.router)
api_router.include_router(transactions.router)
