import uuid
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ---------------------------------------------------------------------------
# CONFIG — edit these two things before deploying
# ---------------------------------------------------------------------------

YOUR_EMAIL = "24f3002870@ds.study.iitm.ac.in"  # <-- put YOUR actual logged-in email here

ALLOWED_ORIGINS = [
    "https://app-y17rgi.example.com",   # your assigned origin (do not remove)
    "https://exam.sanand.workers.dev/tds-2026-05-ga2",    # <-- replace with the ACTUAL exam page origin
]

RATE_LIMIT = 14        # B: max requests allowed
WINDOW_SECONDS = 10    # per this many seconds


# ---------------------------------------------------------------------------
# Middleware 1 — Request Context
# ---------------------------------------------------------------------------

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        request_id = incoming_id if incoming_id else str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Middleware 3 — Per-client Rate Limiting
# (defined here, registered before context middleware below)
# ---------------------------------------------------------------------------

client_requests = defaultdict(deque)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.time()

        timestamps = client_requests[client_id]

        # Drop timestamps that have aged out of the window
        while timestamps and now - timestamps[0] > WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        timestamps.append(now)

        return await call_next(request)


# ---------------------------------------------------------------------------
# Register middleware
# NOTE: In Starlette, middleware added LAST runs FIRST (outermost).
# We want CORS to wrap everything (including 429 responses), so it's
# added last.
# ---------------------------------------------------------------------------

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": YOUR_EMAIL,
        "request_id": request.state.request_id,
    }
