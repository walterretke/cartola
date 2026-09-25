from fastapi import APIRouter
from app.api.v1.endpoints import users

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
# Adicione outros routers aqui (ex: auth, profiles, push_notifications, etc)
