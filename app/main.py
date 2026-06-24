from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.api import router
from app.outbox.service import get_outbox_relay
from core.database.database import init_database
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("startup: begin")
    outbox_relay = get_outbox_relay()
    try:
        await init_database()
    except Exception as exc:
        logger.warning("startup: database unavailable (%s), continuing", exc)
    try:
        await outbox_relay.start()
    except Exception as exc:
        logger.warning("startup: outbox relay unavailable (%s), continuing", exc)
    yield
    await outbox_relay.stop()
    logger.debug("shutdown: complete")


app = FastAPI(
    title="Payment Processor",
    description="Async payment processing microservice",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(router)
