"""Konfigurasi aplikasi dari environment variable (12-factor app).

Tidak ada secret yang di-hardcode di source code.
"""

import os


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Task Manager API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_COLOR: str = os.getenv("APP_COLOR", "blue").strip().lower()

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/tasks.db",
    )

    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost"
        ).split(",")
        if origin.strip()
    ]

    RATE_LIMIT_ENABLED: bool = _get_bool("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "60/minute")

    def validate_color(self) -> None:
        if self.APP_COLOR not in {"blue", "green"}:
            raise ValueError("APP_COLOR harus 'blue' atau 'green'")


settings = Settings()
settings.validate_color()
