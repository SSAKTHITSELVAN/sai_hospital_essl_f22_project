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

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "essl"
    DB_USER: str = "postgres"
    DB_PASS: str = "password"

    # Device 1 (IN Device)
    DEVICE_1_IP:      str = "192.168.1.201"
    DEVICE_1_PORT:    int = 4370
    DEVICE_1_TIMEOUT: int = 30

    # Device 2 (OUT Device)
    DEVICE_2_IP:      str = "192.168.1.4"  # Changed from 192.168.1.35 to actual device IP
    DEVICE_2_PORT:    int = 4370
    DEVICE_2_TIMEOUT: int = 30

    # Legacy support - maps to Device 1
    DEVICE_IP:      str = "192.168.1.201"
    DEVICE_PORT:    int = 4370
    DEVICE_TIMEOUT: int = 30

    # Application
    APP_HOST:              str = "0.0.0.0"
    APP_PORT:              int = 8000
    SYNC_INTERVAL_MINUTES: int = 5

    # CRITICAL: logical day boundary
    # Set AFTER your latest shift end time.
    # Keep early-morning arrivals (around 07:00) in the same day as their
    # afternoon checkout while still grouping overnight punches together.
    DAY_START_TIME: str = "04:00"

    # Attendance thresholds
    PRESENT_HOURS:  float = 9.0
    HALF_DAY_HOURS: float = 4.5

    # Gap-based duplicate detection (Mode B devices)
    # Punches within this many minutes = same check-in/check-out event (duplicate swipes)
    # Increase if your workers take very short breaks; decrease for very quick re-entry
    MIN_BREAK_GAP_MINUTES: int = 30

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