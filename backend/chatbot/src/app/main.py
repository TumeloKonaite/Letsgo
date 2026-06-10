from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes.chat import router as chat_router
from src.app.api.routes.health import router as health_router
from src.app.core.config import Settings
from src.app.core.dependencies import initialize_dependencies, shutdown_dependencies


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_dependencies(app, settings=settings)
        try:
            yield
        finally:
            shutdown_dependencies(app)

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings.cors_origins if settings is not None else ["http://localhost:3000"]
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "AI Digital Twin API with Memory"}

    app.include_router(health_router)
    app.include_router(chat_router)
    return app


class _LazyApp:
    def __init__(self) -> None:
        self._app: FastAPI | None = None

    def _get_app(self) -> FastAPI:
        if self._app is None:
            self._app = create_app()
        return self._app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._get_app()(scope, receive, send)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_app(), name)


app = _LazyApp()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
