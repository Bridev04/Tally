from fastapi import APIRouter

from app.api.routes import ai_expense, anomalies, auth, dashboard, imports, privacy, protected, reports, subscriptions, transactions


api_router = APIRouter()
api_router.include_router(ai_expense.router)
api_router.include_router(anomalies.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(imports.router)
api_router.include_router(privacy.router)
api_router.include_router(protected.router)
api_router.include_router(reports.router)
api_router.include_router(subscriptions.router)
api_router.include_router(transactions.router)
