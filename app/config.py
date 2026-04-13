# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from datetime import time


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "essl"
    DB_USER: str = "postgres"
    DB_PASS: str = "password"

    # ── Device ──────────────────────────────────────────────────
    DEVICE_IP:      str = "192.168.1.201"
    DEVICE_PORT:    int = 4370
    DEVICE_TIMEOUT: int = 30

    # ── Application ─────────────────────────────────────────────
    APP_HOST:               str   = "0.0.0.0"
    APP_PORT:               int   = 8000
    SYNC_INTERVAL_MINUTES:  int   = 5

    # ── Day boundary ────────────────────────────────────────────
    # Work-day starts at this clock time (HH:MM, 24-hour).
    # Punches are grouped into a "logical day" that spans
    # DAY_START_TIME today  →  DAY_START_TIME tomorrow.
    DAY_START_TIME: str = "04:00"

    # ── Attendance thresholds ────────────────────────────────────
    PRESENT_HOURS:  float = 9.0
    HALF_DAY_HOURS: float = 4.5

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def day_start(self) -> time:
        h, m = map(int, self.DAY_START_TIME.split(":"))
        return time(h, m)


@lru_cache()
def get_settings() -> Settings:
    return Settings()