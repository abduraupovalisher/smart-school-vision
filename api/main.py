from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.logging_config import setup_logging
from api.routes.diagnostics import router as diagnostics_router
from api.routes.isapi import router as isapi_router
from database import engine
from models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Smart School Vision API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(isapi_router, prefix="/api")
app.include_router(diagnostics_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
