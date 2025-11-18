from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from datetime import time


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    
    # Device Configuration
    DEVICE_IP: str
    DEVICE_PORT: int = 4370
    DEVICE_TIMEOUT: int = 30
    
    # Application Configuration
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SYNC_INTERVAL_MINUTES: int = 5
    
    # Shift Timings
    SHIFT_A_START: str = "07:00"
    SHIFT_A_END: str = "15:00"
    SHIFT_B_START: str = "15:00"
    SHIFT_B_END: str = "23:00"
    SHIFT_C_START: str = "23:00"
    SHIFT_C_END: str = "07:00"
    SHIFT_G_START: str = "09:00"
    SHIFT_G_END: str = "17:00"
    
    # Grace periods (minutes)
    LATE_GRACE_MINUTES: int = 15
    EARLY_LEAVE_GRACE_MINUTES: int = 15
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def shift_timings(self) -> dict:
        """Get shift timings as time objects"""
        return {
            "A": {
                "start": self._parse_time(self.SHIFT_A_START),
                "end": self._parse_time(self.SHIFT_A_END),
                "name": "Morning Shift"
            },
            "B": {
                "start": self._parse_time(self.SHIFT_B_START),
                "end": self._parse_time(self.SHIFT_B_END),
                "name": "Afternoon Shift"
            },
            "C": {
                "start": self._parse_time(self.SHIFT_C_START),
                "end": self._parse_time(self.SHIFT_C_END),
                "name": "Night Shift"
            },
            "G": {
                "start": self._parse_time(self.SHIFT_G_START),
                "end": self._parse_time(self.SHIFT_G_END),
                "name": "General Shift"
            }
        }
    
    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse time string to time object"""
        hour, minute = map(int, time_str.split(":"))
        return time(hour, minute)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()