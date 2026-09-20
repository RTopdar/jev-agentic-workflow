from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import init_db
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Jev Agentic Chat", lifespan=lifespan)
app.include_router(api_router)
