from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from .database import engine
from .kafka import producer
from .limiter import limiter
from .routers.orders import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await producer.start()
    yield
    await producer.stop()


app = FastAPI(title="Orders Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429, content={"detail": "Rate limit exceeded"}
    ),
)

app.include_router(router, tags=["orders"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'orders')"
                )
            ).scalar()

            if not result:
                return {"status": "error", "message": "Orders table not found"}, 503

            conn.execute(text("SELECT 1 FROM orders LIMIT 1"))

            return {"status": "ok", "database": "connected", "orders_table": "exists"}
    except Exception as e:
        return {"status": "error", "message": f"Database check failed: {str(e)}"}, 503
