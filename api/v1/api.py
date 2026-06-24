from importlib import import_module

from fastapi import APIRouter
from core.settings import settings

names = (
    "health",
    "payment",
)

if settings.ENVIRONMENT != "prod":
    names = (*names, "test_hooks")

__all__ = ("router",)

router = APIRouter(prefix="/api/v1")
for name in names:
    module = import_module(f"api.v1.endpoints.{name}")
    router.include_router(module.router)
