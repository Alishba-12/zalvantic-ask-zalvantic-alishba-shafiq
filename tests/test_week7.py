import os
import tempfile

os.environ["ASKZ_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["RATE_LIMIT"] = "5/minute"
os.environ.setdefault("GROQ_API_KEY", "test")

from fastapi.testclient import TestClient

from askz import api, logdb
from askz.privacy import anonymise


def fake_stream(question):
    yield ("token", "Hello ")
    yield ("token", "there")
    yield ("sources", ["a.md"])
    yield ("outcome", "unanswered" if "unknown" in question else "answered")


api.stream_answer = fake_stream
client = TestClient(api.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_anonymise():
    out = anonymise("mail me at ali@example.com or call +92 311 979 3409, see https://x.com/a")
    assert "@" not in out and "979" not in out and "http" not in out


def test_chat_streams_and_logs_unanswered():
    r = client.post("/chat", json={"question": "unknown thing, mail a@b.com"})
    assert r.status_code == 200
    assert "event: token" in r.text and "event: done" in r.text
    rows = logdb.unanswered()
    assert rows and "a@b.com" not in rows[0][0]


def test_unanswered_page():
    r = client.get("/admin/unanswered")
    assert r.status_code == 200 and "Unanswered" in r.text


def test_cors_header():
    r = client.options("/chat", headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" in r.headers


def test_rate_limit():
    codes = [client.post("/chat", json={"question": "hi"}).status_code for _ in range(8)]
    assert 429 in codes
