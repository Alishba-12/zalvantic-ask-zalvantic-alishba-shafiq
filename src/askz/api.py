"""Week 7: FastAPI service. POST /chat (SSE), GET /health, CORS, rate limit, privacy-friendly log."""
import html
import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import logdb
from .privacy import anonymise
from .service import stream_answer

RATE_LIMIT = os.environ.get("RATE_LIMIT", "10/minute")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Ask Zalvantic")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
@limiter.limit(RATE_LIMIT)
def chat(request: Request, body: ChatRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is empty")

    def events():
        outcome = "answered"
        try:
            for kind, value in stream_answer(question):
                if kind == "outcome":
                    outcome = value
                else:
                    yield _sse(kind, value)
        except Exception:
            outcome = "unanswered"
            yield _sse("error", "Something went wrong. Please try again.")
        finally:
            logdb.log_question(anonymise(question), outcome)
        yield _sse("done", "ok")

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/admin/unanswered", response_class=HTMLResponse)
def unanswered_page(token: str = ""):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = logdb.unanswered()
    body = "".join(
        f"<tr><td>{html.escape(q)}</td><td>{n}</td></tr>" for q, n, _ in rows
    ) or "<tr><td colspan=2>Nothing here yet.</td></tr>"
    return (
        "<!doctype html><meta charset=utf-8><title>Unanswered questions</title>"
        "<style>body{font-family:sans-serif;max-width:720px;margin:2rem auto}"
        "td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left}</style>"
        "<h1>Unanswered questions</h1><p>These are the questions the bot could not answer from the knowledge base.</p>"
        f"<table><tr><th>Question (anonymised)</th><th>Times asked</th></tr>{body}</table>"
    )


if os.path.isdir("widget"):
    app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")
