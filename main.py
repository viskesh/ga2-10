import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# ---------- Config (your assigned values) ----------
ALLOWED_ORIGINS = "https://app-y17rgi.example.com"

WINDOW_SECONDS = 10
MAX_REQUESTS = 14
YOUR_EMAIL = "24f3002870@ds.study.iitm.ac.in"  # <-- put YOUR actual logged-in email here

client_hits = defaultdict(list)


# ---------- Middleware 1: Request context ----------
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------- Middleware 3: Rate limiting ----------
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.time()
        client_hits[client_id] = [t for t in client_hits[client_id] if now - t < WINDOW_SECONDS]

        if len(client_hits[client_id]) >= MAX_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        client_hits[client_id].append(now)
        return await call_next(request)


# Order of add_middleware: LAST added = FIRST to run on the way in.
# We want CORS outermost, so add it LAST.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping(request: Request):
    return {"email": YOUR_EMAIL, "request_id": request.state.request_id}
