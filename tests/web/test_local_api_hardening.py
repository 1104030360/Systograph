from __future__ import annotations

from fastapi import APIRouter
from fastapi.testclient import TestClient

from kai_mind.web.app import create_app


def test_large_request_returns_413_with_cors_header() -> None:
    client = TestClient(
        create_app(max_request_body_bytes=32),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/api/map/build",
        headers={
            "Origin": "http://localhost:5173",
            "Content-Type": "application/json",
        },
        content=b'{"project_path":"' + (b"x" * 80) + b'"}',
    )

    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"detail": "request_too_large"}


def test_unhandled_error_response_is_masked_and_keeps_cors_header() -> None:
    router = APIRouter()

    @router.get("/api/debug/boom")
    def boom() -> None:
        raise RuntimeError(
            "failed at /Users/linjunting/Local_AI_Health_Doctor/.env "
            "with OPENAI_API_KEY=sk-live-secret-value"
        )

    app = create_app()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/api/debug/boom",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"detail": "internal_server_error"}
    assert "sk-live-secret-value" not in response.text
    assert "/Users/linjunting" not in response.text
